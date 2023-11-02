import re
import pathlib
from lxml import etree
import datetime
from eia_crawling.spiders.utils import write_csv, normalize_string


def parse_ep_parliament(year_path: pathlib.Path,
                        year: int,
                        source_xml_path: pathlib.Path,
                        ):

    # Helper for text normalization
    def join_normalize(input_list):
        output = " ".join(input_list)
        output = normalize_string(output)
        output = output.replace('\r', ' ')
        output = re.sub(' +', ' ', output)
        output = output.strip()
        return output

    # Get file name
    source_xml_path = source_xml_path
    file_name = source_xml_path.stem

    # Read source root
    xml = etree.parse(str(source_xml_path))

    # Get header information
    header = xml.xpath("//text")
    date = header[0].attrib['date']
    sections = xml.xpath('//section')
    parsed_output = []
    for section in sections:
        agendanumber = section.attrib['id'].replace('creitem', '')
        agenda_id = ".".join(['en', date.replace('-', ''), agendanumber])
        agenda = section.attrib['title']
        agenda = re.sub(r'\d*\.\s?', '', agenda)
        interventions = section.xpath('.//intervention')
        for intervention in interventions:
            speechnumber = intervention.attrib['id']
            speech_id = ".".join([agenda_id, speechnumber])
            if intervention.attrib['is_mep'] == 'False':
                # Keep only MEPs
                continue
            mep_id = intervention.attrib['speaker_id']
            mode = intervention.attrib['mode']
            speaker = intervention.attrib['name']
            text_list = intervention.xpath('.//text()')
            text = join_normalize(text_list)
            if text == '':
                continue

            parsed_output.append(
                {'date': date,
                 'agenda_id': agenda_id,
                 'agendanumber': agendanumber,
                 'agenda': agenda,
                 'speech_id': speech_id,
                 'speechnumber': speechnumber,
                 'speaker': speaker,
                 'party': '',
                 'national_party': '',
                 'mep_id': mep_id,
                 'text': text,
                 'mode': mode,
                 'language': ''
                 })

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path, data=parsed_output, fieldnames=['date', 'agenda_id', 'agendanumber', 'agenda', 'speech_id', 'speechnumber', 'speaker', 'party', 'national_party', 'mep_id', 'text', 'mode', 'language'])
