import pathlib
from lxml import etree
import datetime
from eia_crawling.spiders.utils import write_csv, normalize_string
import re


def join_normalize(input_list):
    output = " ".join(input_list)
    output = normalize_string(output)
    output = output.strip()
    return output


def parse_polish_parliament(year_path: pathlib.Path,
                            year: int,
                            source_xml_path: pathlib.Path,
                            meta_xml_path: pathlib.Path):
    # Get file name
    source_xml_path = source_xml_path
    file_name = source_xml_path.stem

    year = str(year)

    # Read source root and define namespace for xpath queries
    ns = {'d': 'http://www.tei-c.org/ns/1.0'}
    xml = etree.parse(str(source_xml_path))
    meta_xml = etree.parse(str(meta_xml_path))


    # Get the document specific namespace
    ns['e'] = 'http://www.w3.org/XML/1998/namespace'

    # Get the date of the session
    date = meta_xml.xpath('//d:date/text()', namespaces=ns)
    date = join_normalize(date)
    date = datetime.datetime.strptime(date, '%Y-%m-%d').isoformat()[:10]

    # Further meta data
    title = meta_xml.xpath('//d:titleStmt//text()', namespaces=ns)
    title = join_normalize(title)

    system = meta_xml.xpath('//d:bibl/d:note[@type="system"]/text()', namespaces=ns)
    system = join_normalize(system)

    term_no = meta_xml.xpath('//d:bibl/d:note[@type="termNo"]/text()', namespaces=ns)
    term_no = join_normalize(term_no)

    session_no = meta_xml.xpath('//d:bibl/d:note[@type="sessionNo"]/text()', namespaces=ns)
    session_no = join_normalize(session_no)

    day_no = meta_xml.xpath('//d:bibl/d:note[@type="dayNo"]/text()', namespaces=ns)
    day_no = join_normalize(day_no)

    # Define parliament and iso3country
    parliament = "PL-Zgromadzenie Narodowe"
    iso3country = "POL"

    parsed_output = []

    speech_secs = xml.xpath('//d:div', namespaces=ns)

    i = 0
    for speech_sec in speech_secs:
        paragraph_secs = speech_sec.xpath('.//d:u', namespaces=ns)
        i += 1
        j = 0
        for paragraph_sec in paragraph_secs:
            text = paragraph_sec.xpath('.//text()', namespaces=ns)
            text = join_normalize(text)
            if re.search('^\(.*\)', text):
                continue
            j += 1
            speaker_id = paragraph_sec.xpath('./@who', namespaces=ns)
            speaker_id = join_normalize(speaker_id)
            speaker = meta_xml.xpath(f"//d:person[@e:id='{speaker_id[1:]}']/d:persName/text()", namespaces=ns)
            speaker_name = join_normalize(speaker)
            speaker_uri_raw = meta_xml.xpath(f"//d:person[@e:id='{speaker_id[1:]}']/d:linkGrp/d:ptr/@target", namespaces=ns)
            speaker_uri_raw = join_normalize(speaker_uri_raw)
            if speaker_uri_raw:
                speaker_uri = speaker_uri_raw.split('owl')[1]
            else:
                speaker_uri = ''

            parsed_output.append(
                {'date': date,
                 'title': title,
                 'term': term_no,
                 'session': session_no,
                 'sitting': day_no,
                 'agenda': '',
                 'speechnumber': i,
                 'paragraphnumber': j,
                 'speaker': speaker_name,
                 'speaker_uri': speaker_uri,
                 'party': '',
                 'text': text,
                 'parliament': parliament,
                 'iso3country': iso3country,
                 'system': system
                 })

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path, data=parsed_output,
              fieldnames=['date', 'title', 'term', 'session', 'sitting', 'agenda', 'speechnumber', 'paragraphnumber',
                          'speaker', 'speaker_uri', 'party', 'text',
                          'parliament', 'iso3country', 'system'])
