import pathlib
import datetime
import json
import textract
import numpy as np
from eia_crawling.spiders.utils import write_csv, normalize_string
import re
from sys import platform

# Hard coded reused regex patterns
AGENDA_TITLE_MATCH = r'(?<=__br__)\s*?([a-z\-]*?|([A-Z\-]*?))\s*\d{2}\s*[A-ZÉÀÈÙÂÊÎÔÛ](?![A-ZÉÀÈÙÂÊÎÔÛ]).*?__br____br__'
SPEECH_MATCH = r'__br__\s*(?<!\d)\d{2}\.\d{2,3}(?!\d)\s*.*?\s*:|__br__\s*Le\s*président\s*:|__br__\s*Le\s*président\s*\(.*?\)\s*:'
OPENING_MATCH = r'(La\s*séance\s*est\s*ouverte|La\s*réunion\s*publique\s*est\s*ouverte|La\s*séance\s*d\'hommage\s*est\s*ouverte|La\s*séance\s*est\s*repris)'


def parse_belgian_parliament(year_path: pathlib.Path,
                             year: int,
                             source_pdf_path: pathlib.Path,
                             meta_json_path: pathlib.Path):
    # Build output path for cropped data
    file_name = source_pdf_path.stem

    # Read meta data:
    meta_f = open(meta_json_path, 'r')
    meta_data = json.load(meta_f)
    year = str(year)
    title = meta_data[file_name]['full_title']
    date = title.split('_')[0]
    date = datetime.datetime.strptime(date, '%Y%m%d').isoformat()

    # Define parliament and iso3country
    parliament = "BE-De Kamer"
    iso3country = "BEL"

    parsed_output = []

    data_encoded = textract.process(str(source_pdf_path), encoding='UTF-8', layout=True)
    data = data_encoded.decode('UTF-8')
    # Split on \r\n to retrieve the data per row
    # todo: Code is not operator system independent ==> \r\n on windows as line separator...
    if platform == 'linux':
        raise ValueError("Parsing for this OS not implemented")
    elif platform == 'win32':
        rows = data.split('\r\n')
    else:
        raise ValueError("Parsing for this OS not implemented")

    # Identify in which column the french text is
    french_first = None
    for row in rows:
        opening_statement_match = re.search(OPENING_MATCH, row)
        if opening_statement_match is not None:
            pos = opening_statement_match.start()
            if pos > 20:
                # French data is in second column
                french_first = False
                # # Get the year specific offset
                # if year == '2009':
                #     year_offset = 54
                # elif year == '2015':
                #     year_offset = 51
                # else:
                #     year_offset = 52
                #
                # # If the computed offset is smaller then the year specific offset use the computed offset
                # if year_offset >= pos:
                #     offset = pos
                # else:
                #     offset = year_offset
            else:
                french_first = True
                # Look up the beginning of the "flämisch"
                # offset = row.find('De') - 1
            break

    if french_first is None:
        raise AssertionError

    # # Preprocess the rows, before actual parsing can start
    # # Get the french data
    # rows_processed = []
    # for row in rows:
    #     if not french_first:
    #         row = row[offset:]
    #         # Replace single characters at the beginning of a row as those are probably from the dutch text
    #         row = re.sub('^(\w\s+?)', '', row)
    #     else:
    #         # The columns are swapped in some years
    #         row = row[:offset]
    #         row = re.sub('(\s+?\w)$', '', row)
    #     rows_processed.append(row)
    # french_data = "__br__".join(rows_processed)

    data = "__br__".join(rows)

    # Find the beginning of the text ("La séance est ouverte") introduces each document
    text_start_match = re.search(OPENING_MATCH, data)
    if text_start_match is not None:
        french_text = data[text_start_match.start():]
    else:
        raise AssertionError

    # Keep only the french text
    rows = french_text.split('__br__')
    rows_processed = []
    # Get the french data
    for index, row in enumerate(rows):
        # Consider multiple cases:
        # 1. It is the first row (no dutch text in it)
        # 2. It is normal text (use the longest sequences of spaces to do the splitting)
        #  a. There is only a single language in the row
        # 3. It is an agenda point (start from the french agenda point)
        # 4. It is the beginning of a speech (start from the french beginning of speech)
        # 5. It is a header
        # 6. It is a footer
        # 7. It is a vote table

        if index != 0 and row != '':
            # Is it an agenda point?
            # Pattern: Two digits followed by a uppercase char, then multiple whitespaces followed by the same pattern
            agenda_point_match = re.match(r'^\d{2}\s*[A-ZÉÀÈÙÂÊÎÔÛ](?![A-ZÉÀÈÙÂÊÎÔÛ]).*?\s{2,}(?=\d{2}\s*[A-ZÉÀÈÙÂÊÎÔÛ](?![A-ZÉÀÈÙÂÊÎÔÛ]))', row)
            if agenda_point_match:
                if french_first:
                    row = row[:agenda_point_match.end()]
                else:
                    row = row[agenda_point_match.end():]
            else:
                # Is it the beginning of a speech?
                beginning_of_speech_match = re.match(r'(^\d{2}\.\d{2,3}(?!\d)\s+.*?\s+(?=\s*(?<!\d)\d{2}\.\d{2,3}(?!\d)\s*.*?\s*:))|(^Le\s*président\s*\(?.*?\)?\s*:.*?(?=De\s*voorzitter\s*\(?.*?\)?\s*:))|(^De\s*voorzitter\s*\(?.*?\)?\s*:.*?(?=Le\s*président\s*\(?.*?\)?\s*:))', row)
                if beginning_of_speech_match:
                    if french_first:
                        row = row[:beginning_of_speech_match.end()]
                    else:
                        row = row[beginning_of_speech_match.end():]
                else:
                    # Remove footer
                    footer_match = re.search(r'CHAMBRE.\d[A-Z]\s*SESSION\s*DE\s*LA\s*\d{2}[A-Z]', row)
                    if footer_match:
                        continue
                    else:
                        # Is it a header?
                        header_match = re.search('CRABV\s*\d{2}\s*PLEN\s*\d{3}', row)
                        if header_match:
                            # Indicate a page break
                            row = '__pb__'
                        else:
                            vote_table_match = re.search(r'\(Stemming/vote\s*?\d{1,4}|Ja\s*?\d{1,3}\s*?Oui|Nee\s*?\d{1,3}\s*?Non|Onthoudingen\s*?\d{1,3}\s*?Abstentions|Totaal\s*?\d{1,3}\s*?Total|Stemmen\s*?\d{1,3}\s*?Votants|Blanco\s*?of\s*ongeldig\s*\d{1,3}\s*?Blancs\s*?ou\s*nuls|Geldig\s*\d{1,3}\s*?Valables|Volstrekte\s*\d{1,3}\s*?Majorité|meerderheid\s*meerderheid', row)
                            if vote_table_match:
                                continue
                            else:
                                # Normal text - identify the largest sequence of whitespaces
                                normal_text_matches = re.findall(r'\s{2,}', row)
                                if normal_text_matches:
                                    i_longest_whitespaces = np.array(list(map(len, normal_text_matches))).argmax()
                                    # Split on the longest whitespace to separate french and dutch
                                    rows = row.split(normal_text_matches[i_longest_whitespaces])
                                    if french_first:
                                        row = rows[0]
                                    else:
                                        row = rows[1]
                                else:
                                    # Assume that there is only the first language in the row as there are no whitespaces
                                    if not french_first:
                                        # Only dutch is in the row
                                        continue
        rows_processed.append(row)
    french_text = "__br__".join(rows_processed)
    # Indicate pagebrakes correctly
    french_text = french_text.replace('__br____pb____br__', '__pb__')
    french_text = french_text.replace('\f', '')

    # Get everything starting from the first agenda point
    agenda_point_match = re.search(AGENDA_TITLE_MATCH, french_text)
    if agenda_point_match is not None:
        agenda_point_start = agenda_point_match.start()
    else:
        raise AssertionError
    # Keep the br tags
    french_speech = french_text[agenda_point_start-12:]
    # Remove footer
    # french_speech = re.sub(
    #     '__br__\s*\d*\s*\d*\s*CHAMBRE-\d[A-Z]\s*SESSION\s*DE\s*LA\s*\d{2}[A-Z]\s*[A-ZÉ]{11}\s*(\d{1,4})?\s*__br__', '',
    #     french_speech)
    # Remove header both types of headers
    # And indicate the beginning of a page
    # if french_first:
    #     french_speech = re.sub('__br__\s*\d*\s*CRABV\s*\d{2}\s*PLEN\s*\d{3}\s*\d+(\/)?\d*(\/)?\d*__br__', '__pb__', french_speech)
    #     french_speech = re.sub('__br__\s*\d*\s*\d+(\/)?\d*(\/)?\d*__br__', '__pb__', french_speech)
    # else:
    #     french_speech = re.sub('__br__\s*[\d\/]*\s*CRABV\s*\d{2}\s*PLEN\s*\d{3}\s*__br__', '__pb__', french_speech)
    #     french_speech = re.sub('__br__\s*[\d\/]*\s*\d+__br__', '__pb__', french_speech)
    # Replace \' with '
    french_speech = french_speech.replace("\\'", "'")
    # Treat page breaks that interrupt a paragraph as a new row
    french_speech = re.sub('(__br__)+__pb____br__(?!(__br__))', '__br__', french_speech)
    # Treat the page breaks that match with new paragraph as a new paragraph
    french_speech = re.sub('(__br__){3,}', '__br____br__', french_speech)
    french_speech = re.sub('(__br__)+__pb__(__br__){2}', '__br____br__', french_speech)

    # Init speech count
    i = 0
    # Find all agenda points
    for agenda_title_match in re.finditer(AGENDA_TITLE_MATCH, french_speech):
        # Process each agenda point
        # Parse the agenda title
        agenda_title = agenda_title_match.group()
        agenda_title = re.sub('^\s*[\w\-]+?\s*(?=\d{2})', '', agenda_title)
        agenda_title = re.sub('__br__', ' ', agenda_title)
        agenda_title = re.sub('\s+', ' ', agenda_title).strip()
        # print(agenda_title)

        # Exclude the current agenda title, but keep the breaks
        agenda_text = french_speech[agenda_title_match.end() - 12:]

        # Try to find the next agenda point in order to subset the text
        next_agenda_title_match = re.search(AGENDA_TITLE_MATCH, agenda_text)
        if next_agenda_title_match is not None:
            agenda_text = agenda_text[:next_agenda_title_match.start()]

        # Need to differentiate two cases for the text that is not accounted to anyone:
        # 1. Case there is no speaker within an agenda point
        # 2. There is a speaker, but there is preceding text to the first speaker, that is not accounted to anyone

        # Check whether there is no speaker in the agenda point
        next_speaker_match = re.search(SPEECH_MATCH, agenda_text)
        if next_speaker_match is not None:
            # Subset the non-speaker_text
            non_speaker_text = agenda_text[:next_speaker_match.start()]
        else:
            non_speaker_text = agenda_text

        # Increase the speech number
        i += 1
        # Reset the paragraph number
        j = 0
        # Default empty speaker
        speaker_name = ''
        party = ''
        # todo: Might put this in a separate method as it is a duplicate code fragment
        # Parse the text as a non speaker
        for paragraph in non_speaker_text.split('__br____br__'):
            # Remove leading .
            paragraph = re.sub(r'__br__\s*?[\.!?]', '', paragraph)
            # Remove row breaks
            paragraph = paragraph.replace('__br__', ' ')
            # Remove general comments at the end of a paragraph
            paragraph = re.sub(r'\(.*?\)\s*$', '', paragraph)
            # Remove multiple white spaces
            text = re.sub(r'\s+', ' ', paragraph)
            text = text.strip()

            # Check whether there is something to add to the output
            if text == '':
                continue
            # print(text)

            # Increase the paragraph count
            j += 1

            # Write the result
            parsed_output.append(
                {'date': date,
                 'agenda': agenda_title,
                 'speechnumber': i,
                 'paragraphnumber': j,
                 'speaker': speaker_name,
                 'party': party,
                 'text': text,
                 'parliament': parliament,
                 'iso3country': iso3country
                 })

        # Process the speeches
        # Find the speeches
        for speech_start_match in re.finditer(SPEECH_MATCH, agenda_text):
            # Increase the speech count
            i += 1
            # Reset the paragraph count
            j = 0
            # print(speech_start_match.group())
            # Parse the party only if there is no comma in the speaker string
            party = ''
            party_match = None
            if ',' not in speech_start_match.group():
                party_match = re.search(r'\(.*?\)', speech_start_match.group())
                if party_match is not None and 'président' not in speech_start_match.group():
                    party = party_match.group()
                    party = party[1:-1].replace('__br__', ' ')
                    party = re.sub(r'\s+', ' ', party).strip()
                    # print(party)

            # Parse the speaker <First Name> <Last Name> <(Party)>
            speaker_match = re.search(r'\d{2}\.\d{2,3}\s*.*?\(', speech_start_match.group())
            if speaker_match is not None:
                # Any other member of the parliament is the speaker, get with out the digits and "("
                speaker_name = speaker_match.group()[5:-1].replace('__br__', ' ')
            # Fallback if speaker does not have a party
            else:
                speaker_match = re.search(r'\d{2}\.\d{2,3}\s*.*?:', speech_start_match.group())
                if speaker_match is not None:
                    # Any other member of the parliament is the speaker, get with out the digits and "("
                    speaker_name = speaker_match.group()[5:-1].replace('__br__', ' ')
                # President is the speaker
                else:
                    # get without the ":"
                    speaker_name = speech_start_match.group()[:-1].replace('__br__', ' ')
                    # Clean up anything that is behind the presidents name
                    if party_match is not None:
                        speaker_name = speaker_name.replace(party_match.group(), '')
            speaker_name = re.sub(r'\s+', ' ', speaker_name).strip()
            # print(speaker_name)

            # Subset agenda text
            speech_text = agenda_text[speech_start_match.end():]

            # Try to find the next speaker in order to subset the speech text further
            next_speech_start_match = re.search(SPEECH_MATCH, speech_text)
            if next_speech_start_match is not None:
                speech_text = speech_text[:next_speech_start_match.start()]

            # Process the paragraphs of each speech
            for paragraph in speech_text.split('__br____br__'):
                # Remove leading .
                paragraph = re.sub(r'__br__\s*?[\.!?]', '', paragraph)
                # Remove row breaks
                paragraph = paragraph.replace('__br__', ' ')
                # Remove general comments at the end of a paragraph
                paragraph = re.sub(r'\(.*?\)\s*$', '', paragraph)
                # Remove multiple white spaces
                text = re.sub(r'\s+', ' ', paragraph)
                text = text.strip()

                # Check whether there is something to add to the output
                if text == '':
                    continue
                # print(text)

                # Increase the paragraph count
                j += 1

                # Write the result
                parsed_output.append(
                    {'date': date,
                     'agenda': agenda_title,
                     'speechnumber': i,
                     'paragraphnumber': j,
                     'speaker': speaker_name,
                     'party': party,
                     'text': text,
                     'parliament': parliament,
                     'iso3country': iso3country
                     })

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path,
              data=parsed_output,
              fieldnames=['date', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'party', 'text',
                          'parliament', 'iso3country'])
