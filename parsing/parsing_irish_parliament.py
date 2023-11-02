import pathlib
from lxml import etree
import datetime
from eia_crawling.spiders.utils import write_csv, normalize_string
import re


def parse_irish_parliament(year_path: pathlib.Path,
                           year: int,
                           source_xml_path: pathlib.Path):
    # Get file name
    source_xml_path = source_xml_path
    file_name = source_xml_path.stem

    year = str(year)

    # Read source root and define namespace for xpath queries
    ns = {'d': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13'}
    xml = etree.parse(str(source_xml_path))

    # Get the date of the session
    date = file_name.split('_')[0]
    date = datetime.datetime.strptime(date, '%Y%m%d').isoformat()

    # Define parliament and iso3country
    parliament = "IE-House-of-the-Oireachtas"
    iso3country = "IRE"

    parsed_output = []

    debate_secs = xml.xpath('//d:debateSection[not(@name="prelude" or @name="WrittenAnswers" or @name="writtenAnswer")]', namespaces=ns)
    # Process each speech
    j = 0
    i = 0
    for z, debate_sec in enumerate(debate_secs):
        # Get the agenda title of the current debate
        agenda_title = debate_sec.xpath('.//d:heading//text()', namespaces=ns)
        agenda_title = " ".join(agenda_title)
        agenda_title = normalize_string(agenda_title)
        # If still empty, try to get the previous title (there might be falsy debate sections)
        if agenda_title == '' and parsed_output:
            agenda_title = parsed_output[-1].get('agenda', '')
        # If still empty, try to get the previous title (there might be falsy debate sections)
        if agenda_title == '' and z != 0:
            agenda_title = debate_secs[z-1].xpath('.//d:heading//text()', namespaces=ns)
            agenda_title = " ".join(agenda_title)
            agenda_title = normalize_string(agenda_title)
        # Try to find a summary tag below as fallback for the agenda title
        if agenda_title == '':
            agenda_title = debate_sec.xpath('.//d:summary//text()', namespaces=ns)
            agenda_title = " ".join(agenda_title)
            agenda_title = normalize_string(agenda_title)
        # Get all speeches
        speeches = debate_sec.xpath('.//d:*[@by]  | .//d:summary', namespaces=ns)
        for speech in speeches:
            # Check whether the speaker is a member of the parliament
            speaker = speech.attrib.get('by', '')

            # Summary tag
            if speaker == '' and 'summary' in speech.tag:
                # Summaries are treated differently, we attribute the summary text to the previous speaker
                if parsed_output:
                    previous_output = parsed_output[-1]
                    speaker_name = previous_output.get('speaker')
                    speaker_uri = previous_output.get('speaker_uri')
                    text = speech.xpath('.//text()')
                    text = " ".join(text)
                    text = normalize_string(text)

                    # Increase paragraph count as this attributed to the previous speaker
                    j += 1

                    # Check late to ensure that the agenda title is relevant
                    if agenda_title == '':
                        raise AssertionError

                    parsed_output.append(
                        {'date': date,
                         'agenda': agenda_title,
                         'speechnumber': i,
                         'paragraphnumber': j,
                         'speaker': speaker_name,
                         'speaker_uri': speaker_uri,
                         'text': text,
                         'parliament': parliament,
                         'iso3country': iso3country
                         })
                else:
                    # If nothing was parsed yet, we cannot determine who said it
                    continue

            # Normal speeches
            else:
                # Standard way
                speaker_name = ''
                speaker_uri = ''
                if speaker != "#":
                    # Get the name and the Uri to the members database
                    try:
                        person = xml.xpath(f'//d:TLCPerson[@eId="{speaker[1:]}"]', namespaces=ns)[0]
                    except:
                        raise AssertionError
                    speaker_uri = person.attrib['href']
                    speaker_name = person.attrib['showAs']
                if speaker_name == '':
                    # Get the name from the "from" field
                    try:
                        speaker_name = speech.xpath('./d:from', namespaces=ns)[0].text
                    except:
                        # Get from the by attribute and then parse it
                        speaker_name = speech.attrib.get('by', '')
                        speaker_name = speaker_name.lstrip('#')
                        # Split on uppercase letter
                        speaker_name = re.sub(r"([A-Z])", r" \1", speaker_name).split()
                        speaker_name = " ".join(speaker_name)
                if speaker_name == '':
                    raise AssertionError

                # Process the statements of each speech
                paragraphs = speech.xpath('.//d:p', namespaces=ns)
                if not paragraphs:
                    raise AssertionError

                # Increase speech count as a new speech started and reset paragraph count
                i += 1
                j = 0
                for paragraph in paragraphs:
                    text = paragraph.xpath('.//text()')
                    text = " ".join(text)
                    j += 1
                    # Cannot check for empty string as this might happen due to malformed XML

                    text = normalize_string(text)

                    # Check late to ensure that the agenda title is relevant
                    if agenda_title == '':
                        raise AssertionError

                    parsed_output.append(
                        {'date': date,
                         'agenda': agenda_title,
                         'speechnumber': i,
                         'paragraphnumber': j,
                         'speaker': speaker_name,
                         'speaker_uri': speaker_uri,
                         'text': text,
                         'parliament': parliament,
                         'iso3country': iso3country
                         })

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path, data=parsed_output,
              fieldnames=['date', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'speaker_uri', 'text',
                          'parliament', 'iso3country'])
