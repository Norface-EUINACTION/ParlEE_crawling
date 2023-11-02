import pathlib
import datetime
import json
import textract
import numpy as np
from eia_crawling.spiders.utils import write_csv, normalize_string
import re
from sys import platform


def parse_slovakian_parliament(year_path: pathlib.Path,
                               year: int,
                               source_doc_path: pathlib.Path):
    # Build output path for cropped data
    file_name = source_doc_path.stem

    # Read meta data
    year = str(year)
    file_name_list = file_name.split("_")
    legislature = int(file_name_list[1])
    try:
        meeting = int(file_name_list[2])
    except:
        meeting = file_name_list[2]
    date_raw = file_name_list[3]
    date = datetime.datetime.strptime(date_raw, '%Y%m%d').isoformat()

    # Define parliament and iso3country
    parliament = "SK-N\u00e1rodn\u00e1 rada"
    iso3country = "SVK"

    parsed_output = []

    data_encoded = textract.process(str(source_doc_path), encoding='UTF-8', layout=True)
    data = data_encoded.decode('UTF-8')
    # Split on \r\n to retrieve the data per row
    # todo: Code is not operator system independent ==> \r\n on windows as line separator...
    if platform == 'linux':
        raise ValueError("Parsing for this OS not implemented")
    elif platform == 'win32':
        pass
    else:
        raise ValueError("Parsing for this OS not implemented")

    # Replace \n\r with __br__ for easier readability in strings
    data = re.sub(r'[\n\r]', '__br__', data)

    # Find the beginning of speeches
    if legislature == 4:
        speeches_match = list(re.finditer(r'(?<=__br____br__)[A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ][a-záäčďéíĺľňóôŕšťúýž]?\.\s+[A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ].*?,\s+.*?:\s+', data))
    else:
        speeches_match = list(
            re.finditer(r'(?<=__br____br____br__)([A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ][a-záäčďéíĺľňóôŕšťúýž]+([-\s][A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ][a-záäčďéíĺľňóôŕšťúýž]+)?,\s+[A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ][a-záäčďéíĺľňóôŕšťúýž]+([-\s][A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ][a-záäčďéíĺľňóôŕšťúýž]+)?,\s+.*?)(?=__br____br__)', data))

    # Init speechnumber
    i = 0

    for index, speech_match in enumerate(speeches_match):
        # Subset the data to the beginning of the match until the beginning of the next match
        if index + 1 < len(speeches_match):
            # We did not reach the end of the list, then subset like this
            speech_raw = data[speech_match.end():speeches_match[index+1].start()]
        else:
            speech_raw = data[speech_match.end():]

        # Identify the speaker
        speaker_raw = speech_match.group(0)
        speaker_raw_list = speaker_raw.split(",")
        if legislature == 4:
            speaker = normalize_string(speaker_raw_list[0])
            speakerrole_raw = ",".join(speaker_raw_list[1:]).strip(" :")
            speakerrole = normalize_string(speakerrole_raw)
        else:
            speaker = normalize_string(",".join(speaker_raw_list[:2]))
            speakerrole_raw = ",".join(speaker_raw_list[2:]).strip(" :")
            speakerrole = normalize_string(speakerrole_raw)

        # Identify the text
        speech_raw_list = speech_raw.split("__br____br__")
        # Set speech- and paragraphnumber
        i += 1
        j = 0
        for paragraph in speech_raw_list:
            paragraph = re.sub(r'\(.*?\)', '', paragraph)
            if not re.search(r'[A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽa-záäčďéíĺľňóôŕšťúýž]', paragraph):
                continue
            j += 1
            text = normalize_string(paragraph)
            # normalize_string does not strip left white spaces, adding it might endanger compatibility to other parliaments
            text = text.strip()


            # Write the result
            parsed_output.append(
                {'date': date[:10],
                 'agenda': np.nan,
                 'speechnumber': i,
                 'paragraphnumber': j,
                 'speaker': speaker,
                 'speakerrole': speakerrole,
                 'party': np.nan,
                 'text': text,
                 'legislature': legislature,
                 'meeting': meeting,
                 'parliament': parliament,
                 'iso3country': iso3country
                 })

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path,
              data=parsed_output,
              fieldnames=['date', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'speakerrole', 'party', 'text',
                          'legislature', 'meeting', 'parliament', 'iso3country'])
