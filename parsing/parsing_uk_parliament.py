import re
import pathlib
from scrapy.http import HtmlResponse
import datetime
import locale
import numpy as np
from eia_crawling.spiders.utils import write_csv, normalize_string


# Helper method
def join_normalize(input_list):
    output = " ".join(input_list)
    output = normalize_string(output)
    output = output.replace('\r', ' ')
    output = re.sub(' +', ' ', output)
    output = output.strip()
    return output


def parse_uk_parliament(year_path: pathlib.Path,
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
    parliament = "UK-HouseOfCommons"
    iso3country = "GBR"

    date_list_raw = response.xpath('//div[@data-tag="hs_6fDate"]//text()').getall()
    date_raw = join_normalize(date_list_raw)
    date_raw = join_normalize(date_raw.split()[1:][:3])
    locale.setlocale(locale.LC_ALL, 'en_GB')
    date = datetime.datetime.strptime(date_raw, '%d %B %Y').isoformat()

    speaker_dict = {}
    speechnumber = 0

    # Loop through agenda
    for agenda in response.xpath('//div[@class="child-debate"]'):
        agenda_title_list_raw = agenda.xpath('./h2//text()').getall()
        agenda_title = join_normalize(agenda_title_list_raw)

        # Get all speeches
        for speech in agenda.xpath('.//div[@class="debate-item debate-item-contributiondebateitem"]'):
            speaker = ''
            speakerrole = ''
            party = ''
            text = ''

            # Get the speaker related information
            header = speech.xpath('.//div[@class="header"]')
            speaker_list_raw = header.xpath('.//div[@class="primary-text"]//text()').getall()
            speaker = join_normalize(speaker_list_raw)
            additional_info_list_raw = header.xpath('.//div[@class="secondary-text"]//text()').getall()
            if additional_info_list_raw:
                additional_info = join_normalize(additional_info_list_raw)
                # Two cases (either the name is in there or the district + the party is in there)
                if re.search(r'\(.*\)\s+\(.*\)', additional_info):
                    # District + party case
                    party = re.search(r'(?<=\)\s\().*(?=\))', additional_info).group(0)
                    party = normalize_string(party)
                elif re.search(r'\(.*\)', additional_info):
                    # Speaker name
                    speakerrole = speaker
                    speaker = re.search(r'(?<=\().*(?=\))', additional_info).group(0)

                speaker = re.sub('^\s*(Mrs|Mr|Ms|Dr)\s*', '', speaker)
                # Get rid of white spaces when hyphens are used
                speaker = re.sub(r'\s?-\s?', '-', speaker)
                speaker = re.sub(r'^Sir\s', '', speaker)
                speaker = normalize_string(speaker)
                speaker = speaker.strip()

                # Store entities in the same way as they are mentioned in the text
                if speakerrole != '' and not speaker_dict.get(speakerrole, None):
                    speaker_dict[speakerrole] = {
                        'name': speaker
                    }
                else:
                    speaker_dict[speaker] = {
                        'party': party
                    }
            else:
                # Dirty fix: Hard code some special namings for a few persons
                if 'Speaker' in speaker:
                    # Naming convention introduced by other dataset we use to merge our data with
                    speaker = 'CHAIR'

                # Get rid of white spaces when hyphens are used and of 'Sir'
                speaker = re.sub(r'\s?-\s?', '-', speaker)
                speaker = re.sub(r'^Sir\s', '', speaker)

                # Special case of naming
                if re.search('^\s*(Mrs|Mr|Ms|Dr)\s*', speaker):
                    # Get the matching names
                    last_name = re.sub('^\s*(Mrs|Mr|Ms|Dr)\s*', '', speaker)
                    last_name = last_name.strip()
                    matching = [name for name in speaker_dict.keys() if last_name in name]
                    if len(matching) == 1:
                        # Could find the correct naming
                        speaker = matching[0]
                    elif len(matching) > 1:
                        # There are multiple speakers that have that name
                        raise AssertionError

                # In case we don´t have additional information check the speaker dict
                entity = speaker_dict.get(speaker, None)
                if entity is not None:
                    name = entity.get("name", None)
                    if name is not None:
                        speakerrole = speaker
                        speaker = name
                    else:
                        party = entity.get("party", '')

            # Fix some naming conventions
            speaker = re.sub(r'\.', '', speaker)

            # Get the actual text
            text_raw_list = speech.xpath('.//div[@class="content"]//text()').getall()
            text = join_normalize(text_raw_list)
            if text == '':
                continue
            speechnumber += 1

            # Align party naming
            if party == 'PC':
                party = 'PlaidCymru'
            elif party == 'Green':
                party = 'GPEW'
            elif party == 'LD':
                party = 'LibDem'
            elif party == 'Lab/Co-op':
                party = 'Lab'
            elif party == 'Alliance':
                party = 'APNI'

            parsed_output.append(
                {'date': date[:10],
                 'agenda': agenda_title,
                 'speechnumber': speechnumber,
                 'paragraphnumber': '',
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
              fieldnames=['date', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker',
                          'speakerrole', 'party', 'text', 'parliament', 'iso3country'])
