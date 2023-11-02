import json
import pathlib
import unicodedata
import locale
from scrapy.http import HtmlResponse
import datetime
import re
from eia_crawling.spiders.utils import write_csv

# Agenda points that are not specifically marked in the HTML, but used in the existing Austrian data
REOCCURRING_AGENDA_POINTS = ['Beginn der Sitzung',
                             'Aktuelle Stunde',
                             'Einlauf und Zuweisungen',
                             'Behandlung der Tagesordnung',
                             'Fragestunde',
                             'Aktuelle Europastunde']


def parse_austrian_parliament(year_path: pathlib.Path,
                              year: int,
                              source_html_path: pathlib.Path,
                              meta_json_path: pathlib.Path):
    # Get file name
    file_name = source_html_path.stem

    # Read meta data:
    meta_f = open(meta_json_path, 'r')
    meta_data = json.load(meta_f)

    # Get some meta data
    url = meta_data[file_name]['URL']

    # Read source html
    source_f = open(source_html_path, "rb")
    source_html = source_f.read()
    response = HtmlResponse(url=url, body=source_html)

    # Get parsed main text
    parsed_output = []

    # Define parliament and iso3country
    parliament = "AT-Nationalrat"
    iso3country = "AUT"

    # Get the date
    date_list = response.xpath(
        '//p[@class="ZM" and contains(text(), "Dauer der Sitzung")]/following-sibling::p[1]//text()').getall()
    date = " ".join(date_list)
    date = unicodedata.normalize('NFKC', date)
    date = date.replace('\r\n', ' ')
    date = re.search('(?<=, ).*?(?=: )', date)
    if date is not None:
        date = date.group()
        # Parse the date into date time
        locale.setlocale(locale.LC_TIME, 'de_AT')
        date = datetime.datetime.strptime(date, '%d. %B %Y')
    else:
        # Could not parse date
        raise AssertionError

    # Find the wordsections of the speech
    wordsections = response.xpath('//p[@class="SB"]/following::div[contains(@class, "WordSection")]')

    # Init speech and paragraph count
    i, j = 0, 0
    # Go over each wordsection
    for wordsection in wordsections:
        # Find all paragraphs in that wordsection
        paragraphs = wordsection.xpath(
            './p[(@class="MsoNormal" or @class="StandardRB" or @class="MsoBodyText" or @class="StandardRE") and not(b and (not(text()) and not(self::text()) and not(span/text()))) and not(a[contains(@name, "TEXTOBJ")])]')
        current_speaker = ''
        party = ''
        for paragraph in paragraphs:
            # Process each paragraph bottom up (i.e. take each paragraph and find speaker and agenda title)
            # Find the correct agenda title (splitted in two parts, for example first part: 1. Punkt, second part: Bla Bla Bla)
            agenda_match_1 = paragraph.xpath('((./preceding::a[contains(@name, "TOP_")]/parent::p[@class="ZM"])|(./preceding::a[contains(@name, "TEXTOBJ")]/parent::p)|(./preceding::p[@class="SB"]))')
            if agenda_match_1:
                # Define which element to take from the selector list as it matches all agenda points
                k = -1
                # In case of TEXTOBJ we need to ensure that we are not at "Beginn of Sitzung" as behaviour is different
                if agenda_match_1[k-1].xpath('self::p[@class="SB"]'):
                    # In that case we are at "Beginn of Sitzung"
                    agenda_match_1 = paragraph.xpath('./preceding::p[@class="SB"][1]')
                # Check whether agenda match is on the right node, correct if not
                if not agenda_match_1[k].xpath('./descendant-or-self::text()'):
                    # In this case the anchor of the agenda point is at a page break. We need to identfiy the node with the agenda title first
                    # Search for the next p element with class ZM in the tree
                    agenda_match_1 = agenda_match_1.xpath('./following-sibling::p[(@class="ZM" or @class="SB") and descendant-or-self::text()][1]')
                    if not agenda_match_1:
                        raise AssertionError
                # Check whether the agenda point is simply a timestamp/no text in there, in that case delete the agenda point
                if agenda_match_1[k].xpath('self::p[a[contains(@name, "TEXTOBJ")] and not(span/text() or text())]'):
                    del agenda_match_1[k]
                # Check whether a TEXTOBJ is embedded into a speaker
                if agenda_match_1[k].xpath('self::p[@class="MsoNormal" and a[contains(@name, "TEXTOBJ")] and b/a]'):
                    del agenda_match_1[k]
                # Check whether agenda point has a second part
                # agenda_match_2 = agenda_match_1[k].xpath('./following-sibling::p[not(b and (self::text() or text() or span/text()))]')
                agenda_match_2 = agenda_match_1[k].xpath(
                    './following-sibling::p[@class="ZM" and not(contains(text(), "*****") or contains(span/text(), "*****")) or @class="MsoNormal" and (b/text() or b/span/text()) and not(b and (self::text() or text() or span/text()))]')
                # Check whether the agenda point is followed by further agenda points in case
                agenda_title_list_2 = agenda_match_2.xpath('.//text()').getall()
                if agenda_title_list_2 is None:
                    agenda_title_list_2 = []
                # Parse the agenda title
                agenda_title_list_1 = agenda_match_1[k].xpath('.//text()').getall()
                agenda_title_list_1.extend(agenda_title_list_2)
                agenda_title = " ".join(agenda_title_list_1)
                agenda_title = unicodedata.normalize('NFKC', agenda_title)
                agenda_title = agenda_title.replace('\r\n', ' ')
                agenda_title = re.sub('\s+', ' ', agenda_title)
                # Merge long words that are seperated by "-"
                agenda_title = re.sub('(\&shy;|­)\s?', '', agenda_title)
                # In that case the session was interrupted and we need to take the previous agenda point
                if re.search('^\d{2}\.\d{2}\.\d{2}\s?$', agenda_title):
                    agenda_title = parsed_output[-1].get("agenda")
                else:
                    agenda_title = re.sub('\d{2}\.\d{2}\.\d{2}\s?', '', agenda_title)
                if agenda_title is None or agenda_title == '':
                    # Something went wrong
                    raise AssertionError
            else:
                agenda_title = "Einleitung"

            # Find the speaker for each paragraph
            if bool(paragraph.xpath('./descendant::b[descendant::a]')):
                # The paragraph belongs to a new speaker
                current_speaker_list = paragraph.xpath('./descendant::b[descendant::a]//text()').getall()
                if not current_speaker_list:
                    raise AssertionError
                current_speaker = " ".join(current_speaker_list)
                current_speaker = unicodedata.normalize('NFKC', current_speaker)
                current_speaker = current_speaker.replace('\r\n', ' ')
                current_speaker = re.sub('\s+', ' ', current_speaker)
                # Merge long words that are seperated by "-"
                current_speaker = re.sub('(\&shy;|­)\s?', '', current_speaker)
                current_speaker = current_speaker.strip(' :')

                # Increase speech count as a new speaker was found
                i += 1
                # Reset paragraph count as a new speech started
                j = 0

            # Parse the speech
            speech_list = paragraph.xpath('.//text()[not(ancestor::i[not(parent::b)])]').getall()
            speech = " ".join(speech_list)
            # Get rid of undecodeable characters
            speech = unicodedata.normalize('NFKC', speech)
            # Get rid of line breaks
            speech = speech.replace('\r\n', ' ')
            # Get rid of multiple whitespaces
            speech = re.sub('\s+', ' ', speech)
            # Merge long words that are seperated by "-"
            speech = re.sub('(\&shy;|­)\s?', '', speech)
            # Remove the speaker from the beginning
            speech = speech.replace(current_speaker, '')

            # New speech started
            if j == 0:
                party_match = re.search('\(\w+\)\s:', speech)
                if party_match is not None:
                    # Get the party string
                    party = party_match.group()
                    # Remove the party string from the speech
                    speech = speech.replace(party, '')
                    # Parse the party string to the party only
                    party = party.strip('() :')
                elif re.search('\(fortsetzend\):', speech):
                    # If a speaker is interrupted the party is not mentioned again, but only the name
                    # Hence, need to find the party in the previous entries
                    for row in reversed(parsed_output):
                        if current_speaker == row.get('speaker'):
                            party = row.get('party')
                            break
                    fortsetzend = re.search('\(fortsetzend\):', speech).group()
                    speech = speech.replace(fortsetzend, '')
                else:
                    party = ''

            # Some speeches contain the :
            speech = speech.lstrip(' :')
            speech = speech.rstrip()

            # Skip lines that do not have any content ()
            if speech == '':
                continue

            # Increase the paragraph count
            j += 1

            parsed_output.append(
                {'date': date,
                 'agenda': agenda_title,
                 'speechnumber': i,
                 'paragraphnumber': j,
                 'speaker': current_speaker,
                 'party': party,
                 'text': speech,
                 'parliament': parliament,
                 'iso3country': iso3country
                 })

    # Paragraphs are separated due to header and footer of page. Use simple heuristic to merge them back together
    # Is inefficient, but should do the job
    # Additionally replace "*****" agenda points by the previous one
    current_speech_number = None
    index_correction = 0
    for index, row in enumerate(parsed_output):

        if row.get("agenda") == "*****":
            row["agenda"] = parsed_output[index-1].get("agenda")

        # Reset if speech number changed
        if current_speech_number != row.get("speechnumber"):
            # Reset the remembered variables
            current_speech_number = None
            index_correction = 0

        if not re.search('[.?!“;]$', row.get("text")) and index != len(parsed_output)-1:
            # Remember the current speech number
            current_speech_number = row.get("speechnumber")
            # Get the text of the next line and concatenate it to the current one
            if parsed_output[index+1].get("speechnumber") == current_speech_number:
                next_text = parsed_output[index+1].get("text")
                row["text"] = row.get('text') + " " + next_text
                # Ensure that no double spaces exist
                row["text"] = re.sub('\s+', ' ', row["text"])
                # Merge long words that are seperated by "-"
                row["text"] = re.sub('(\&shy;|-)\s', '', row["text"])
                # Delete the next line
                del parsed_output[index+1]
                # Correct own index as well, but with old index correction value
                row["paragraphnumber"] = row.get("paragraphnumber") - index_correction
                # For each time such a behavior is discovered we need to correct the paragraph index by 1
                index_correction += 1
                # Continue to avoid running into index correction of paragraph number
                continue

        # Correct the paragraph number
        if current_speech_number == row.get("speechnumber") and index_correction != 0:
            row["paragraphnumber"] = row.get("paragraphnumber") - index_correction

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path, data=parsed_output,
              fieldnames=['date', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'party', 'text', 'parliament',
                          'iso3country'])
