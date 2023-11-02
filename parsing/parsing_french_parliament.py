import json
import pathlib
from scrapy import Selector
from scrapy.http import HtmlResponse
from lxml import html
import datetime
from eia_crawling.spiders.utils import write_csv, normalize_string

MONTHS = {
    'janvier': '1',
    'février': '2',
    'mars': '3',
    'avril': '4',
    'mai': '5',
    'juin': '6',
    'juillet': '7',
    'août': '8',
    'septembre': '9',
    'octobre': '10',
    'novembre': '11',
    'décembre': '12'
}


def parse_french_parliament(year_path: pathlib.Path,
                            year: int,
                            source_html_path: pathlib.Path,
                            meta_json_path: pathlib.Path):

    # Get file name
    source_html_path = source_html_path
    file_name = source_html_path.stem

    # Read meta data:
    meta_f = open(meta_json_path, 'r')
    meta_data = json.load(meta_f)

    # Get some meta data
    year = str(year)
    url = meta_data[file_name]['URL']

    # Read source html
    source_f = open(source_html_path, "rb")
    source_html = source_f.read()
    response = HtmlResponse(url=url, body=source_html)

    # Get parsed main text
    parsed_output = []

    # Get the date (need to handle few exceptional date formulations)
    date_list = response.xpath('//h1[not(parent::div[@id="somjo"])]/text()[not(parent::sup)]').getall()
    # Check whether date is empty
    if not date_list:
        # Try to get the date from the title
        date_list = response.xpath('//title//text()').getall()
    if date_list:
        date_list = [x.strip('\n ') for x in date_list]
        date = " ".join(date_list)
        date = date.split()[-3:]
        # Replace month with number
        date[1] = MONTHS[date[1]]
        # Secure that day is only the number (first elements of the string)
        if len(date[0]) > 2:
            # Exclude st, nd, rd
            date[0] = date[0][:-2]
        date = ".".join(date)
        # Create datetime
        date = datetime.datetime.strptime(date, '%d.%m.%Y').isoformat()
    else:
        # No date retrieved
        raise AssertionError


    # Case 1 and case 2: all politicians speeches are in a paragraph each surrounded by a div
    if response.xpath('//div[@class="Point"]').get() is not None:
        politician_paragraphs = response.xpath('//h2[@class="titre1"]/following::p[b]')
    # Case 3a: Multiple paragraphs form one politician speech
    elif response.xpath(
            '//h2[@class="titre1"]/following::p[text() and not(@class) and not(ancestor::ul)]').get() is not None:
        politician_paragraphs = response.xpath(
            '//h2[@class="titre1"]/following::p[text() and not(@class) and not(ancestor::ul)]')
    # Case 3b: Exceptional transcripts e.g. C001 from 2009
    else:
        politician_paragraphs = response.xpath(
            '//div[@id="englobe"]//p[text() and not(@class) and not(ancestor::ul) and not(@style)]')

    if not politician_paragraphs:
        # No paragraphs retrieved
        raise AssertionError

    j = 0
    speaker_name_previous = ''
    # Get all politician speeches
    for z, politician_paragraph in enumerate(politician_paragraphs):
        # Find the preceding top level agenda title
        agenda_title_list = politician_paragraph.xpath('./preceding::h5[1]/following-sibling::h2[@class="titre1"][1]//text()').getall()
        if not agenda_title_list and response.xpath('//div[@id="somjo"]').get() is None:
            # If there is no agenda, we cannot infer an agenda title hence take the title
            agenda_title_list = response.xpath('//title//text()').getall()
        if not agenda_title_list:
            # Retry reading of agenda title for differently structured example
            # In case the numbering of agenda points is not used
            agenda_title_list = politician_paragraph.xpath('./preceding::h2[@class="titre1"][1]//text()').getall()
        if not agenda_title_list and z == 0:
            # Fallback for the first agenda title (usually it is the opening of the session)
            agenda_title_list = politician_paragraph.xpath('./preceding::h1[1]//text()').getall()
        if not agenda_title_list:
            # Fall back for weakly structured examples that don´t use the class attribute on the agenda titles
            agenda_title_list = politician_paragraph.xpath('./preceding::h2[1]//text()').getall()

        agenda_title = " ".join(agenda_title_list)


        # Handle speaker name (in case there is no speaker assign the last know speaker)
        speaker_name_current = politician_paragraph.xpath('./b//text()').get()
        if speaker_name_current is None:
            speaker_name_current = ''
        # Remove salutation
        speaker_name_current = " ".join(speaker_name_current.split()[1:])
        # Remove political role
        speaker_name_current = speaker_name_current.split(',')[0]
        if speaker_name_current == '' and speaker_name_previous != '':
            speaker_name_current = speaker_name_previous
            i += 1
        elif speaker_name_current == '' and speaker_name_previous == '':
            # Assume that this paragraph is noise
            continue
        else:
            speaker_name_previous = speaker_name_current
            j += 1
            i = 1

        # Handle speech
        # In case 1 and 2 each politician paragraph needs to be split on br tags in case it has them
        if response.xpath('//div[@class="Point"]').get() is not None and \
                politician_paragraph.xpath('./br').get() is not None:
            politician_paragraph_html = html.fromstring(politician_paragraph.get())
            for br in politician_paragraph_html.xpath('br'):
                if br.tail is None:
                    br.drop_tree()
                else:
                    br.tail = '__br__' + br.tail
                    br.drop_tree()
            politician_paragraph = Selector(
                HtmlResponse(url=url, body=html.tostring(politician_paragraph_html)))

        speech_list = politician_paragraph.xpath('.//text()[../b and not(b) or sup]').getall()
        # Handle case 3, there are speeches that do not have a direct speaker
        if not speech_list:
            speech_list = politician_paragraph.xpath('.//text()').getall()
        speech_full = " ".join(speech_list)
        for k, speech in enumerate(speech_full.split('__br__')):
            # In case there are br-tags there are multiple paragraphs in that speech
            if k > 0:
                i = k + 1
            # Check for empty parameters
            if not agenda_title or not speaker_name_current:
                raise AssertionError
            # Normalize agenda title, speaker and speech
            agenda_title = normalize_string(agenda_title)
            speaker_name_current = normalize_string(speaker_name_current)
            speech = normalize_string(speech)

            parsed_output.append(
                {'date': date,
                 'agenda': agenda_title,
                 'speechnumber': j,
                 'paragraphnumber': i,
                 'speaker': speaker_name_current,
                 'text': speech,
                 'parliament': 'FR-Assemblee-Nationale',
                 'iso3country': 'FRA'
                 })

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path, data=parsed_output, fieldnames=['date', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'text', 'parliament', 'iso3country'])