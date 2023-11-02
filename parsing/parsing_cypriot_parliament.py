import pathlib
import codecs
import datetime
import re
import numpy as np

from eia_crawling.spiders.utils import normalize_string, write_csv

GREEK_ALPHABET = 'Α-ΩὉΪᾺ\u1FEA'


def normalize_string_cyprus(string):
    string = normalize_string(string)
    return string.strip()


def parse_cypriot_parliament(year_path: pathlib.Path,
                             year: int,
                             source_txt_path: pathlib.Path):
    # Build output path for cropped data
    file_name = source_txt_path.stem

    year = str(year)
    file_name_list = file_name.split('_')
    date = datetime.datetime.strptime(file_name_list[0], '%Y-%m-%d').isoformat()

    # Get term, session and sitting
    term = file_name_list[1]
    session = file_name_list[2]
    sitting = file_name_list[3]

    # Define parliament and iso3country
    parliament = "CY-Temsilciler Meclisi"
    iso3country = "CYP"

    parsed_output = []

    with codecs.open(str(source_txt_path), encoding='utf-8') as f:
        session_data_raw = f.readlines()
        session_data_raw = " ".join(session_data_raw)
    session_data = session_data_raw.replace('\r\n', '__br__')
    session_data = re.sub(r'\s\s+', ' ', session_data)

    # Replace page numbering
    session_data = re.sub(r'__br__\s\d{1,3}(?=__br__)', '', session_data)

    # Replace up-arrows (result of OCR)
    session_data = re.sub(r'__br__\s\u000C', '', session_data)

    # Capitalize the agenda to prevent confusion with speaker names
    session_data = re.sub(r'(?<=__br__)\sΚΕΦΑΛΑΙΟ\s.*?:', lambda x: x.group().title(), session_data)

    # Discard everything after the sitting is closed
    end_match = list(re.finditer(r'__br__\s[\({]Ώρα (λήξης)?.*?[\)}](?=__br__)', session_data))
    if end_match:
        if len(end_match) > 1:
            # print("Sitting interrupted")
            pass
        session_data = session_data[:end_match[-1].start()]
    else:
        # There must be an end match
        raise AssertionError

    role_to_speaker = {}

    speaker_matches = list(re.finditer(rf'(?<=__br__)\s*[{GREEK_ALPHABET}]+(͂:|:)(?=__br__)|(?<=__br__)\s*[{GREEK_ALPHABET}]+((-\.|\.|-)?[\s\-][{GREEK_ALPHABET}]+)+(͂:|:|\.)(?=__br__)', session_data))
    for i, speaker_match in enumerate(speaker_matches):
        # init some variables
        speakerrole = ''

        if speaker_match:
            # Check whether the last item of the list is reached, for sub setting the session data
            if i < len(speaker_matches) - 1:
                current_speech_raw = session_data[speaker_match.end():speaker_matches[i+1].start()]
            else:
                current_speech_raw = session_data[speaker_match.end():]

            # Get the speaker and his/her role
            # At this stage the speaker name might still be a speaker role
            speaker = speaker_match.group().strip(" .:͂:͂")
            speaker = normalize_string_cyprus(speaker)

            if re.match(r'^__br__\s(__br__\s)?(ΤΊ|\d+(?=__br__))', current_speech_raw):
                current_speech_raw = re.sub(r'^__br__\s(__br__\s)?(ΤΊ|\d+)', '', current_speech_raw)

            if re.search(rf'^__br__\s(__br__\s)?\([{GREEK_ALPHABET}]+((-\.|\.|-)?[\s\-][{GREEK_ALPHABET}]+)*(Ὶ\)|\)|Ὶ)?__br__', current_speech_raw):
                # The speaker match contains the speaker role and the name is in brackets
                speaker_name_match = re.search(rf'^__br__\s(__br__\s)?\([{GREEK_ALPHABET}]+((-\.|\.|-)?[\s\-][{GREEK_ALPHABET}]+)*(Ὶ\)|\)|Ὶ)?__br__', current_speech_raw)
                speaker_name_raw = speaker_name_match.group()
                speaker_name = re.sub(r'__br__', '', speaker_name_raw)
                speaker_name = speaker_name.strip("() Ὶ")
                speakerrole = speaker
                speaker = normalize_string_cyprus(speaker_name)

                # In this case add or update the speaker role in the dictionary
                role_to_speaker[speakerrole] = speaker

                # Clean up the text
                current_speech_raw = current_speech_raw[speaker_name_match.end():]
                current_speech_raw = current_speech_raw.strip(' ()')
            elif speaker in role_to_speaker:
                # The speaker is actually a speaker role and the mapping is already recorded
                speakerrole = speaker
                speaker = role_to_speaker[speakerrole]

            # Remove written passages in the data
            paragraphs = re.split(r'(?=\(Η σχετική ἐκθεση\)|\(Οι ερωτήσεις των βουλευτών\)|\(Η σχετική τροπολογία\)|\(Οι σχετικές τροπολογίες\)|\(Οι σχετικές εκθέσεις\)|\(Η κατάθεση νομοσχεδίων και ἐεγγράφων\))', current_speech_raw)

            j = 0
            for current_paragraph_raw in paragraphs:
                if re.search(r'\(Η σχετική ἐκθεση\)|\(Οι ερωτήσεις των βουλευτών\)|\(Η σχετική τροπολογία\)|\(Οι σχετικές τροπολογίες\)|\(Οι σχετικές εκθέσεις\)|\(Η κατάθεση νομοσχεδίων και ἐεγγράφων\)', current_paragraph_raw):
                    current_paragraph_raw = re.sub(r'^(\(.*?\))\s*(?=__br__)', r'<<<\1>>>', current_paragraph_raw)
                    is_written = True
                else:
                    is_written = False

                current_paragraph_raw = re.sub(r'(?<=__br__)\s(\(.*?\))\s*(?=__br__)', r'<<<\1>>>', current_paragraph_raw)
                # Get the text
                current_paragraph = current_paragraph_raw.replace('__br__', ' ')
                current_paragraph = normalize_string_cyprus(current_paragraph)

                if current_paragraph == '':
                    continue

                j += 1

                parsed_output.append(
                    {'date': date[:10],
                     'title': file_name,
                     'agenda': '',
                     'speechnumber': i+1,
                     'paragraphnumber': j,
                     'speaker': speaker,
                     'speakerrole': speakerrole,
                     'party': '',
                     'text': current_paragraph,
                     'written': is_written,
                     'term': term,
                     'session': session,
                     'sitting': sitting,
                     'parliament': parliament,
                     'iso3country': iso3country,
                     })

        else:
            # There must be at least one speaker
            raise AssertionError

    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path, data=parsed_output,
              fieldnames=['date', 'title', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker',
                          'speakerrole', 'party', 'text', 'written', 'term', 'session', 'sitting', 'parliament', 'iso3country'])