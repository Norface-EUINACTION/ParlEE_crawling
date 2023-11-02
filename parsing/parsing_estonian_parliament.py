import re
import json
import pathlib
from scrapy.http import HtmlResponse
import datetime
from eia_crawling.spiders.utils import write_csv, normalize_string


def parse_estonian_parliament(year_path: pathlib.Path,
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
    # Replace <br> with __br__ to split on it later
    source_html = source_html.decode('UTF-8').replace('<br/>', '__br__').encode('UTF-8')
    response = HtmlResponse(url=url, body=source_html)

    # Get the date of the session (many possible formats)
    date = file_name.split("_")[0]
    date = datetime.datetime.strptime(date, '%Y%m%d').isoformat()

    # Define parliament and iso3country and title
    title_raw_list = response.xpath('//header[@class="steno-header"]//h2//text()').getall()
    title_raw = " ".join(title_raw_list)
    title = normalize_string(title_raw)
    title = re.sub(r'\s+__br__\s+', ', ', title)
    parliament = "EE-Riigikogu"
    iso3country = "EST"

    parsed_output = []

    i = 0

    # Get paragprahs:
    speeches = response.xpath('//div[@class="pb-4 speech-area"]')
    party = ''
    for speech in speeches:
        # Get text
        text_raw_list = speech.xpath('./div//text()').getall()
        if text_raw_list:
            # New speech started
            i += 1
            j = 0
            speech_text_raw = " ".join(text_raw_list)
            speech_text = normalize_string(speech_text_raw)
            # Split on __br__ to identify paragraphs
            texts = speech_text.split("__br__")
            for text in texts:
                # Remove brackets at the end of a text as those indicate comments on the speech
                text = re.sub(r'\(.*?\)$', '', text)
                text = text.strip()
                if text != '':
                    j += 1
                    # Identify speaker:
                    speaker_raw_list = speech.xpath('./h4//text()').getall()
                    if speaker_raw_list:
                        speaker_raw = " ".join(speaker_raw_list)
                        speaker = normalize_string(speaker_raw)
                    else:
                        raise AssertionError

                    # Identify speakerrole
                    if re.search(r'^.*?simees\s+', speaker):
                        speakerrole_raw = re.search(r'^.*?simees', speaker).group()
                        speaker = speaker.replace(speakerrole_raw, ' ')
                        speakerrole = normalize_string(speakerrole_raw)
                        speaker = normalize_string(speaker)
                    elif re.search(r'^.*?minister\s+', speaker):
                        speakerrole_raw = re.search(r'^.*?minister', speaker).group()
                        speaker = speaker.replace(speakerrole_raw, ' ')
                        speakerrole = normalize_string(speakerrole_raw)
                        speaker = normalize_string(speaker)
                    elif re.search(r'^.*?kantsler\s+', speaker):
                        speakerrole_raw = re.search(r'^.*?kantsler', speaker).group()
                        speaker = speaker.replace(speakerrole_raw, ' ')
                        speakerrole = normalize_string(speakerrole_raw)
                        speaker = normalize_string(speaker)
                    elif re.search(r'^Valitsuse nõunik\s+', speaker):
                        speakerrole_raw = re.search(r'^Valitsuse nõunik', speaker).group()
                        speaker = speaker.replace(speakerrole_raw, ' ')
                        speakerrole = normalize_string(speakerrole_raw)
                        speaker = normalize_string(speaker)
                    else:
                        speakerrole = ''
                    # Identify agenda point
                    agenda_raw_list = speech.xpath('./parent::article[1]/h3//text()').getall()
                    if agenda_raw_list:
                        agenda_raw = " ".join(agenda_raw_list)
                        agenda_title = normalize_string(agenda_raw)
                        agenda_title = agenda_title.replace("<br/>", "")
                    else:
                        agenda_title = ''

                    parsed_output.append(
                        {'date': date[:10],
                         'title': title,
                         'agenda': agenda_title,
                         'speechnumber': i,
                         'paragraphnumber': j,
                         'speaker': speaker,
                         'speakerrole': speakerrole,
                         'party': party,
                         'text': text,
                         'parliament': parliament,
                         'iso3country': iso3country
                         })

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path, data=parsed_output,
              fieldnames=['date', 'title', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'speakerrole', 'party',
                          'text', 'parliament',
                          'iso3country'])
