import re
import pathlib
from scrapy.http import HtmlResponse
import datetime
import numpy as np
from eia_crawling.spiders.utils import write_csv, normalize_string


# Helper method
def join_normalize(input_list):
    output = " ".join(input_list)
    output = normalize_string(output)
    output = output.strip()
    return output


def parse_romanian_parliament(year_path: pathlib.Path,
                              year: int,
                              source_html_path: pathlib.Path):
    # Get file name
    source_html_path = source_html_path
    file_name = source_html_path.stem

    # Read source html
    source_f = open(source_html_path, "rb")
    source_html = source_f.read()
    response = HtmlResponse(url="", body=source_html)

    parsed_output = []

    # Define parliament and iso3country
    parliament = "RO-Camera Deputaților"
    iso3country = "ROU"

    # Get date
    date_list_raw = response.xpath('//td[@class="cale2"]/text()').getall()
    if date_list_raw:
        date = join_normalize(date_list_raw)
        date = date.strip(" >")
        date = datetime.datetime.strptime(date, '%d-%m-%Y').isoformat()
    else:
        raise AssertionError

    if re.search(r'\s\d$', file_name):
        sitting = file_name[-1]
    else:
        sitting = 1

    title_list_raw = response.xpath('//span[@class="headline"][1]//text()').getall()
    title = join_normalize(title_list_raw)

    i = 0
    speaker_found = False

    # Get the whole speech
    speeches_raw = response.xpath('//td[@class="textn" and @width="100%" and not(i)]')
    for speech_raw in speeches_raw:
        # Check if there is a speaker at beginning of the speech. Speakers are weakly marked in the HTML, hence we need to check twice
        if speech_raw.xpath('./p/b/a[descendant::text()]|./p/b[descendant::text()]'):
            # Get the speaker
            speaker_list_raw = speech_raw.xpath('./p/b[descendant::text()][1]//text()').getall()
            speaker = join_normalize(speaker_list_raw)
            # Match two capitalized words for a speaker (be sure that we have a speaker)
            if re.search(r'^[A-ZĂÂÎȘȚ][a-zăâîșț]*\s+[A-ZĂÂÎȘȚ][a-zăâîșț]*', speaker):
                speaker_found = True
                speakerrole_raw_list = speech_raw.xpath('./*[self::p and descendant::text()][1]/descendant::i//text()').getall()
                if speakerrole_raw_list:
                    speakerrole = join_normalize(speakerrole_raw_list)
                    speakerrole = speakerrole.strip(")(: ")
                else:
                    speakerrole = ''
            else:
                speaker_found = False
        else:
            speaker_found = False

        # Get the text
        text_raw_list = speech_raw.xpath('.//*[not(self::i) and text()]/text()').getall()
        text = join_normalize(text_raw_list)
        text = text.strip('*')

        if text != '':
            if speaker_found:
                i += 1
                # Parse out speaker from beginning of text
                # Get out the speakerrole (it is italic)
                # speaker = re.sub(rf'\s*\(\s*{speakerrole}\s*\)\s*:?', '', speaker)
                try:
                    text = re.sub(rf'^\s*{speaker}\s*:?', '', text)
                except:
                    raise AssertionError
                text = text.strip()

                # Clean speaker (Mr, Mrs and the speakerrole)
                speaker = re.sub(r'Domnul\s*|Doamna\s*', '', speaker)
                speaker = speaker.strip(': ')
                if speakerrole != '':
                    role_dict[speaker] = speakerrole
            elif parsed_output:
                try:
                    parsed_output[-1]["text"] = parsed_output[-1]["text"] + " " + text
                except:
                    raise AssertionError
                # We add this speech to the previous paragraph then we don´t need to append anything
                continue
            else:
                # We are at the beginning of the speech probably there are some general introductory words
                continue
        else:
            # IF there is no text there is nothing to add to the parsed output
            continue

        if speaker == '':
            raise AssertionError

        if speakerrole == '':
            speakerrole = role_dict.get(speaker, '')

        parsed_output.append(
            {'date': date[:10],
             'sitting': sitting,
             'title': title,
             'agenda': np.nan,
             'speechnumber': i,
             'paragraphnumber': np.nan,
             'speaker': speaker,
             'speakerrole': speakerrole,
             'party': np.nan,
             'text': text,
             'parliament': parliament,
             'iso3country': iso3country
             })


    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path, data=parsed_output,
              fieldnames=['date', 'sitting', 'title', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker',
                          'speakerrole', 'party', 'text', 'parliament', 'iso3country'])
