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
    output = output.replace('\r', ' ')
    output = re.sub(' +', ' ', output)
    output = output.strip()
    return output


def parse_bulgarian_parliament(year_path: pathlib.Path,
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
    parliament = "BG-Narodno sabranie"
    iso3country = "BGR"

    # Get date
    date_list_raw = response.xpath('//div[@class="mb-3"]/text()').getall()
    if date_list_raw:
        date = join_normalize(date_list_raw)
        date = date.strip(" ")
        date = datetime.datetime.strptime(date, '%d/%m/%Y').isoformat()
    else:
        raise AssertionError

    title_list_raw = response.xpath('//div[@class="mb-3"]/h2//text()').getall()
    title = join_normalize(title_list_raw)

    # Get raw text
    raw_session_text_list = response.xpath('//div[@class="mt-4"]//text()').getall()
    raw_session_text = " ".join(raw_session_text_list)

    # Replace \n\r with __br__ for easier readability in strings
    data = re.sub(r'[\n\r]', '__br__', raw_session_text)
    # data = raw_session_text

    i = 0
    speeches_match = list(re.finditer(r"(?<=__br__)(([\u0410-\u042F]{2,}|[\u0410-\u042F]\.|[\u0410-\u042F]{2,}\s*-\s*[\u0410-\u042F]{2,}|[\u0410-\u042F]{2,}\sи)\s+)+([\u0410-\u042F]+|[\u0410-\u042F]{2,}\s*-\s*[\u0410-\u042F]{2,})\s*(:?\s+\([\w\s,]+?\))?(?!__br__):", data, re.MULTILINE))
    agenda_matches = list(re.finditer(r'(?<=__br__)([\u0410-\u042F\d]+[\.?!,;\-\s]+)+([\u0410-\u042F\d])+[\.?!]?\s{,2}?(?!=:)(?=__br__)', data))
    for index, speech_match in enumerate(speeches_match):
        # Subset the data to the beginning of the match until the beginning of the next match
        if index + 1 < len(speeches_match):
            # We did not reach the end of the list, then subset like this
            speech_raw = data[speech_match.end():speeches_match[index + 1].start()]
        else:
            speech_raw = data[speech_match.end():]

        # Identify the speaker
        speaker_raw = speech_match.group(0)
        speaker = normalize_string(speaker_raw)

        if re.search(r'\(.*?\)', speaker):
            party_raw = re.search(r'(?<=\().*?(?=\))', speaker).group()
            party = party_raw.split(',')[0]
            party = normalize_string(party)
            speaker = re.sub(r'\(.*?\)', '', speaker)
        else:
            party = ''

        speakerrole = ''
        # Get very prominent speaker roles
        if re.search(r'(ЗАМЕСТНИК МИНИСТЪР - ПРЕДСЕДАТЕЛ|МИНИСТЪР-ПРЕДСЕДАТЕЛ|ЗАМЕСТНИК МИНИСТЪР-ПРЕДСЕДАТЕЛ|ЗАМЕСТНИК-МИНИСТЪР|ЗАМЕСТНИК|ПРЕДСЕДАТЕЛ|ДОКЛАДЧИК|МИНИСТЪР)\s+', speaker):
            speakerrole = re.search(r'(ЗАМЕСТНИК МИНИСТЪР - ПРЕДСЕДАТЕЛ|МИНИСТЪР-ПРЕДСЕДАТЕЛ|ЗАМЕСТНИК МИНИСТЪР-ПРЕДСЕДАТЕЛ|ЗАМЕСТНИК-МИНИСТЪР|ЗАМЕСТНИК|ПРЕДСЕДАТЕЛ|ДОКЛАДЧИК|МИНИСТЪР)\s+', speaker).group()
            speaker = re.sub(rf'{speakerrole}', '', speaker)
            speakerrole = speakerrole.strip()

        # Make sure all whitespaces are stripped
        speaker = speaker.strip(': ')

        text = speech_raw.replace('__br__', ' ')
        text = normalize_string(text)
        text = text.strip()
        if text == '':
            continue
        # Increase speech count
        i += 1

        # Get the correct agenda item for the speech
        agenda = ''
        for agenda_match in reversed(agenda_matches):
            # Go trough the agenda matches in reversed order to find the agenda closest to the speech
            if speech_match.start() > agenda_match.end():
                agenda_raw = agenda_match.group()
                agenda = normalize_string(agenda_raw)
                agenda = agenda.strip()
                break

        parsed_output.append(
            {'date': date[:10],
             'title': title,
             'agenda': agenda,
             'speechnumber': i,
             'paragraphnumber': np.nan,
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
              fieldnames=['date', 'title', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker',
                          'speakerrole', 'party', 'text', 'parliament', 'iso3country'])
