import re
import pathlib
from lxml import etree
import datetime
from eia_crawling.spiders.utils import write_csv, normalize_string


def parse_german_parliament(year_path: pathlib.Path,
                            year: int,
                            source_xml_path: pathlib.Path):

    # Get file name
    source_xml_path = source_xml_path
    file_name = source_xml_path.stem

    year = str(year)

    # Read source root
    xml = etree.parse(str(source_xml_path))

    # Get the date of the session
    date = str(xml.xpath("//dbtplenarprotokoll/@sitzung-datum")[0])
    date = datetime.datetime.strptime(date, '%d.%m.%Y').isoformat()

    # Define parliament and iso3country
    parliament = "DE-Bundestag"
    iso3country = "GER"

    parsed_output = []

    # Get "Tagesordnungspunkte"
    debate_secs = xml.xpath('//tagesordnungspunkt')
    if not debate_secs:
        raise AssertionError
    i = 0
    j = 0
    for debate_sec in debate_secs:
        agenda_title = debate_sec.xpath('./p[1][@klasse="T_fett"]//text()')
        agenda_title = " ".join(agenda_title)
        agenda_title = normalize_string(agenda_title)
        if agenda_title == '':
            # Fallback to the id of the "tagesordnungspunkt"
            agenda_title = debate_sec.attrib['top-id']
        if agenda_title == '':
            raise AssertionError

        # Get all the paragraphs that are not agenda titles and speakers
        paragraphs = debate_sec.xpath('.//p[not(@klasse="T_fett") and not(@klasse="redner")] | .//kommentar[contains(text(), "]:") and contains(text(), "[") and ./ancestor::sitzungsverlauf]')
        if not paragraphs:
            raise AssertionError
        speaker_name_previous = ''
        # Process each paragraph
        for paragraph in paragraphs:

            # Normal p tag
            if paragraph.tag != 'kommentar':
                # Find the first preceding speaker element
                try:
                    speaker_name_element = paragraph.xpath('./preceding::name[ancestor::sitzungsverlauf] | ./preceding::p[@klasse="N" and ancestor::sitzungsverlauf]')[-1]
                except:
                    raise AssertionError
                # The name element is not embedded into a p of class "redner"
                if speaker_name_element.xpath('./text()'):
                    try:
                        speaker_name_current = speaker_name_element.xpath('./text()')
                        speaker_name_current = " ".join(speaker_name_current)
                        speaker_name_current = re.sub('^[\s]+|[\s]+$', '', speaker_name_current)
                    except:
                        raise AssertionError
                else:
                    try:
                        speaker_name_current = speaker_name_element.xpath('../../text()')
                        speaker_name_current = " ".join(speaker_name_current)
                        speaker_name_current = re.sub('^[\s]+|[\s]+$', '', speaker_name_current)
                    except:
                        raise AssertionError
                if speaker_name_current is None or speaker_name_current == '':
                    # Might happen if the only text is a line feed due to wrong formatting
                    try:
                        speaker_name_current = speaker_name_element.xpath('../../text()')
                        speaker_name_current = " ".join(speaker_name_current)
                        speaker_name_current = re.sub('^[\s]+|[\s]+$', '', speaker_name_current)
                    except:
                        raise AssertionError
                if speaker_name_current == '':
                    raise AssertionError
                speaker_name_current = speaker_name_current.strip(' :')
                if speaker_name_current != speaker_name_previous:
                    # A new speech started
                    # Increase speech count
                    # Reset paragraph count
                    i += 1
                    j = 1
                else:
                    # Still the same speech
                    # Increase paragraph count
                    j += 1
                # Get the party from the speaker name, usually it is in brackets
                party = re.findall('\([^)]*\)', speaker_name_current)
                if party:
                    party = party[-1].strip('()')
                else:
                    party = ''
                speaker_name_previous = speaker_name_current

                # Get the speech
                # Cannot check whether there is no text in this paragraph due to malformed protocols
                # Would run into an error and we wouldn´t know whether this is correct or not
                text = paragraph.xpath('.//text()')
                text = " ".join(text)
                text = normalize_string(text)

                parsed_output.append(
                    {'date': date,
                     'agenda': agenda_title,
                     'speechnumber': i,
                     'paragraphnumber': j,
                     'speaker': speaker_name_current,
                     'party': party,
                     'text': text,
                     'parliament': parliament,
                     'iso3country': iso3country
                     })


            # In case of comments parsing is done differently, try to match the pattern of actual speeches
            elif paragraph.tag == 'kommentar':
                # Get the speech
                # Cannot check whether there is no text in this paragraph due to malformed protocols
                # Would run into an error and we wouldn´t know whether this is correct or not
                text = paragraph.xpath('.//text()')
                text = " ".join(text)
                text = normalize_string(text)

                content = text.split(' – ')
                for x in content:
                    # Try to parse the text according to the regex pattern
                    # Usually it looks like "Max Mustermann [City] [Party]: I am unhappy!"
                    try:
                        speaker_name = re.search('[a-zA-ZßüÜäÄöÖ\s\.\-]*\[.*\]:', x).group()
                        speaker_name_current = speaker_name.strip('(: ').replace('[', '(').replace(']', ')')
                        party = re.findall('\([^)]*\)', speaker_name_current)[-1].strip('()')
                        text = re.search(']:.*', x).group()
                        text = text.strip(']:)')
                        text = normalize_string(text)
                    except AttributeError or IndexError:
                        continue
                    # Add each comment as new speech with a single paragraph
                    i += 1
                    j = 1
                    speaker_name_previous = speaker_name_current

                    parsed_output.append(
                        {'date': date,
                         'agenda': agenda_title,
                         'speechnumber': i,
                         'paragraphnumber': j,
                         'speaker': speaker_name_current,
                         'party': party,
                         'text': text,
                         'parliament': parliament,
                         'iso3country': iso3country
                         })

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path, data=parsed_output, fieldnames=['date', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'party', 'text', 'parliament', 'iso3country'])