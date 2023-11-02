import pathlib
from eia_crawling.spiders.utils import write_csv
import re
from tika import parser
import datetime

parliament = "Eduskunta"
iso3country = "FIN"

AGENDA_TITLE_MATCH = '^(\d{1,2}\. ).{5,}$'
# Speech match with accents
SPEECH_MATCH = "^(((\d{1,2}\.\d{2}) )([A-ZÀ-Ÿ]([a-zÀ-ÿA-ZÀ-Ÿ\-\.]{1,}\s+))(([A-Za-zÀ-ÿ\-\.]{2,}\s+)){0,5}([A-Za-zÀ-ÿ\-]{2,})(\s+(sdp|ps|kok|kesk|vihr|vas|rkp|kd|liik|sd|r)*\s*\(.*\))*:(\s)+)|(.*(puhemies |Puhemies )(([A-ZÀ-Ÿ\-\.]([a-zÀ-ÿA-ZÀ-Ÿ\-\.]){1,}(\s)*){1,}:(\s)+))|^(([A-ZÀ-Ÿ\-]([a-zÀ-ÿA-ZÀ-Ÿ\-\.]){1,}(\s)*){1,}(sdp|ps|kok|kesk|vihr|vas|rkp|kd|liik|sd|r):(\s)+)|(([A-ZÀ-Ÿ][a-zÀ-ÿA-ZÀ-Ÿ\-\.]{1,}\s+){1,3}:)"

TIME_START_MATCH = "^\d{2}\.\d{2} .*"
OPENING_MATCH = '.*Nimenhuuto.*'
DATE_MATCH = '\d{1,2}\.\d{1,2}\.\d{4}'

HEADLINE_MATCH = "(.*Pöytäkirja PTK.*)"
FOOTNOTE_MATCH = "(.*Valmis.*)"

SPEAKER_CLEAN_MATCH = "^\d{2}\.\d{2}.*"

PARTY_MATCH = "^(sdp|ps|kok|kesk|vihr|vas|rkp|kd|liik|sd|r)"

KESKUSTELU_MATCH = "^Keskustelu(\s)*$"

SENTENCE_ENDERS = ".*[!\.?](\s)*$"

VALMIS_FOOTER_CHECK = ".*Valmis.*"

# cleaning
def skip_unimportant(rows):
    new_rows = []
    i = -5
    while i < (len(rows)-6):
        row = rows[i]

        # Let's check the Valmis footer. If the next line is Valmis, we should skip 6 lines, otherwise 5
        if re.match(VALMIS_FOOTER_CHECK, rows[i+1]):
            if re.match(HEADLINE_MATCH, rows[i+6]):
                new_rows.append(row)
                if re.match(SENTENCE_ENDERS, row):
                    new_rows.append("")
                i += 7
            else:
                new_rows.append(row)
                i += 1
        else:
            if re.match(HEADLINE_MATCH, rows[i+5]):
                new_rows.append(row)
                if re.match(SENTENCE_ENDERS, row):
                    new_rows.append("")
                i += 6
            else:
                new_rows.append(row)
                i += 1
    return new_rows


# clean the empty rows in the beginning:
def clean_blanks_beginning(rows):
    for start in range(len(rows)):
        if rows[start] != "":
            rows = rows[start:]
            return rows

def find_date(rows):
    # Let's find the date_match
    for row in rows[0:30]:
        date_match = re.findall(DATE_MATCH, row)
        if len(date_match) != 0:
            dates = date_match[0].split(".")
            x = datetime.datetime(int(dates[2]), int(dates[1]), int(dates[0]))
            DATE = x.strftime("%Y-%m-%d")
            return DATE


# Find the starting row to parse
def find_start_row(rows):
    for i in range(len(rows)):
        opening_statement_match = re.search(OPENING_MATCH, rows[i])
        if opening_statement_match is not None:
            start_row = opening_statement_match.start()
            return start_row


# This is range(0,50) to test, at the end it will be the whole document
def find_agendas_start_end(start_of_document, end_of_document, rows):
    agendas_start_end = []
    agenda_starts = start_of_document
    i = 0
    while i < end_of_document-1:
        row = rows[i]
        agenda_title_match = re.findall(AGENDA_TITLE_MATCH, row)
        if len(agenda_title_match) != 0 and rows[i-1] == "":  # Agenda found, move forward
            # Start of the agenda topic is here, we will do another block to find where this agenda topic ends
            agenda_starts = i
            if rows[i][-1] == "-":
                AGENDA_TOPIC = rows[i][:-1]
            else:
                AGENDA_TOPIC = rows[i] + " "
            # i update after the first line of agenda
            i+=1
            # If next row is blank, end of agenda topic. We are checking until end of agenda topic
            try:
                while rows[i] != "" and i < end_of_document-2:
                    if rows[i][-1] == "-":
                        AGENDA_TOPIC += rows[i][:-1]
                    else:
                        AGENDA_TOPIC += rows[i]
                        AGENDA_TOPIC += " "

                    i += 1
            except Exception as e:
                print(e)

            next_agenda_number = int(AGENDA_TOPIC.split(".")[0]) + 1
            # Let's find where this agenda ends
            for j in range(agenda_starts + 1, end_of_document):
                # Let's also check the next one is a consecutive topic
                agenda_title_next_match = re.findall(AGENDA_TITLE_MATCH, rows[j])
                if j == end_of_document-1:
                    agenda_ends = end_of_document
                # We check if there is a match then if the next match is in line with next number we are expecting and
                # if the next line is also agenda point or not (if that's the case it's not an agenda)
                elif len(agenda_title_next_match) != 0 and int(rows[j].split(".")[0]) == (next_agenda_number) and len(re.findall(AGENDA_TITLE_MATCH,rows[j+1])) == 0:
                    agenda_ends = j  # Agenda topic starts at i, ends at j, we will check in between
                    break


            agendas_start_end.append([AGENDA_TOPIC, agenda_starts, agenda_ends])

            # we update the i to start from the agenda_ends
            i = agenda_ends
        # Line counter update
        else:
            i+=1
    return agendas_start_end


def find_speakers(AGENDA_TOPIC, agenda_start, agenda_end, rows, speech_number=0):
    speakers = []
    # Looking for a speaker name, we check only from i to j
    SPEECH_NUMBER = speech_number
    try:
        for i in range(agenda_start+1, agenda_end):
            row = rows[i]
            previous_row = rows[i-1]
            # It's a band aid for the speaker names that go to the second line too
            time_start_match = re.match(TIME_START_MATCH, row)
            if time_start_match and len(row.split(":")) == 1:
                row = row + rows[i+1]
                i += 1

            speaker_match = re.findall(SPEECH_MATCH, row)

            if len(speaker_match) != 0 and (previous_row == ""):
                # SPEAKER is found, to get the speaker name we will take all the text until colon, because regex doesn't match correctly due to accents I guess
                # HERE WE GET ALL INFORMATION FROM THAT SPEAKER
                speaker_start_row = i

                SPEECH_NUMBER += 1
                SPEAKER = row.split(':')[0]

                # Replace multiple spaces with one
                SPEAKER = SPEAKER.replace("\s+", " ")
                PARTY = ""
                if SPEAKER[-1] == ")":
                    SPEAKER = SPEAKER.split("(")[0]
                if re.match(SPEAKER_CLEAN_MATCH, SPEAKER):
                    SPEAKER = SPEAKER[5:]

                while SPEAKER[-1] == " ":
                    SPEAKER = SPEAKER[:-1]
                party_check = SPEAKER.split(" ")[-1]
                if re.match(PARTY_MATCH, party_check):
                    PARTY = party_check
                    SPEAKER = SPEAKER[:-len(PARTY)]

                # We should know from where to where this person is speaking
                speaker_end_row = None
                for k in range(speaker_start_row+1, agenda_end):
                    row = rows[k]
                    # We also need to do the same band aid here for the next speaker match
                    time_start_match = re.match(TIME_START_MATCH, rows[k])
                    if time_start_match and len(row.split(":")) == 1:
                        row = row + rows[k+1]

                    speaker_next_match = re.findall(SPEECH_MATCH, row)
                    # We check if we found a new spaker or if there is a blank line, blank line also indicates end of speaker

                    if (len(speaker_next_match) != 0):
                        # THAT SPEAKER SPEAKS FROM speaker_start_row TO speaker_end_row
                        speaker_end_row = k
                        break
                    elif k == (agenda_end-1):
                        speaker_end_row = agenda_end

                if speaker_end_row is None:
                    pass
                # List of agenda, speach_number, speaker, start, end
                # We make another check for the cases where start and end are the same row (which shouldn't happen actually)
                elif speaker_start_row < speaker_end_row:
                    speakers.append([AGENDA_TOPIC, SPEECH_NUMBER, SPEAKER, speaker_start_row, speaker_end_row, PARTY])
    except Exception as e:
        print(e)
            # Now let's find the next speaker


    # Let's save the last_speech_number to pass to next one
    last_speech_number = SPEECH_NUMBER
    return speakers, last_speech_number

def find_paragraphs(SESSION, DATE, parliament, iso3country, AGENDA_TOPIC, SPEECH_NUMBER, SPEAKER, speaker_start_row, speaker_end_row, PARTY, rows):
    parsed_document = []
    # WE WILL GET ALL THE PARAGRAPHS OF THAT SPEAKER FROM speaker_start_row TO speaker_end_row
    PARAGRAPH_COUNTER = 1

    # We get the information from first paragraph after "Mert: "
    row = rows[speaker_start_row]
    end_of_line = row[-1]
    first_paragraph = row.split(":")[1:]
    first_paragraph = " ".join(first_paragraph)

    # We are also checking if the first line ends with "-" or not
    try:
        end_of_line = first_paragraph[-1]
        if end_of_line == "-" or end_of_line == '-':
            first_paragraph += first_paragraph[:-1]
    except Exception as e:
        print(e)


    # First let's get the first paragraph only, bc it has a different structure
    for m in range(speaker_start_row+1, speaker_end_row+1):
        # If it's an empty line, then end of paragraph
        row = rows[m]
        # If the line ends with a "-" don't put a space, because it's half word
        if len(row) == 0:
            paragraph_end_row = m
            break
        else:
            end_of_line = row[-1]
            if end_of_line == "-" or end_of_line == '-':
                first_paragraph += row[:-1]
            else:
                first_paragraph += row
                first_paragraph += " "

        if m == speaker_end_row:
            paragraph_end_row = m
    # Let's append the first_paragraph to out parsed_document
    parsed_document.append(
        {'session': SESSION,
         'date': DATE,
         'agenda': AGENDA_TOPIC,
         'speechnumber': SPEECH_NUMBER,
         'paragraphnumber': PARAGRAPH_COUNTER,
         'speaker': SPEAKER,
         'party': PARTY,
         'text': first_paragraph,
         'parliament': parliament,
         'iso3country': iso3country
         })

    # We start next paragraph from end of previous+1, because it ends at blank line
    paragraph_start_row = paragraph_end_row + 1

    # Let's trim the speaker_end_row to the last blank line:
    while rows[speaker_end_row-1] == "":
        speaker_end_row = speaker_end_row-1

    # We need to find the paragraph end row

    while paragraph_start_row<speaker_end_row:
        # we go inside this loop for every paragraph
        for n in range(paragraph_start_row, speaker_end_row):
            row = rows[n]

            # If it's an empty line, then end of paragraph
            if len(row) == 0:
                paragraph_end_row = n
                break
            if n == speaker_end_row - 1:
                paragraph_end_row = speaker_end_row
                break

        # Last row is found, we will build the paragraph
        paragraph = ""
        # We create the paragraph here
        for p in range(paragraph_start_row, paragraph_end_row):
            row = rows[p]
            end_of_line = row[-1]
            # If the line ends with a "-" don't put a space, because it's half word
            if end_of_line == "-" or end_of_line == '-':
                paragraph += row[:-1]
            else:
                paragraph += row
                paragraph += " "
        # paragraph is ready

        # If the paragraph is too short we will skip
        if len(paragraph) <= 10:
            pass
        # Skips the unimportant lines including only "Keskustelu"
        elif re.match(KESKUSTELU_MATCH, paragraph):
            pass
        else:
            PARAGRAPH_COUNTER += 1
            # We will write the paragraph to the file
            # Write the dictionary #paragraph_counter, speech_number
            parsed_document.append(
                {'session': SESSION,
                 'date': DATE,
                 'agenda': AGENDA_TOPIC,
                 'speechnumber': SPEECH_NUMBER,
                 'paragraphnumber': PARAGRAPH_COUNTER,
                 'speaker': SPEAKER,
                 'party': PARTY,
                 'text': paragraph,
                 'parliament': parliament,
                 'iso3country': iso3country
                 })

        # We reassign the paragraph_start_row
        paragraph_start_row = paragraph_end_row + 1

    return parsed_document


# LETS FINALLY MAKE THE FUNCTION CALLS
def parse_finnish_parliament(source_pdf_path: pathlib,
                             year_path: pathlib.Path,
                             year: int):
    # What is going to be the name of the written file?
    file_name = source_pdf_path.stem
    SESSION = file_name
    rawText = parser.from_file(str(source_pdf_path))
    rows = rawText['content'].splitlines()

    rows = clean_blanks_beginning(rows)

    rows = skip_unimportant(rows)

    '''
    for row in rows:
        print(row)
    '''
    DATE = find_date(rows)

    start_of_document = find_start_row(rows)
    end_of_document = len(rows)

    agendas_start_end = find_agendas_start_end(start_of_document, end_of_document, rows)

    parsed = []
    last_speech_number = 0
    # Agenda finder works well, tested
    for [AGENDA_TOPIC, agenda_start, agenda_end] in agendas_start_end:
        speakers, last_speech_number = find_speakers(AGENDA_TOPIC, agenda_start, agenda_end, rows, last_speech_number)

        for [AGENDA_TOPIC, SPEECH_NUMBER, SPEAKER, speaker_start_row, speaker_end_row, PARTY] in speakers:
            # We add it to the paragraphs list
            paragraphs = find_paragraphs(SESSION, DATE, parliament, iso3country, AGENDA_TOPIC, SPEECH_NUMBER, SPEAKER, speaker_start_row, speaker_end_row, PARTY, rows)
            for paragraph in paragraphs:
                parsed.append(paragraph)

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path,
              data=parsed,
              fieldnames=['date', 'session', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'party', 'text',
                          'parliament', 'iso3country'])




