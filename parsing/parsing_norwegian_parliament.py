import json
import pathlib
import unicodedata
import locale
import requests
from bs4 import BeautifulSoup
import datetime
import re
from eia_crawling.spiders.utils import write_csv
import codecs

# Agenda points that are not specifically marked in the HTML, but used in the existing Austrian data
SECTION_HTML_TAG = ['strtngt_presinnlegg',
                    'strtngt_replikk',
                    'strtngt_hovedinnlegg',
                    ]

SPEAKER_HTML_TAG = ["strtngt_navn"]

PARTY_MAPPING = {
    "AP": "Arbeiderpartiet",
    "A": "Arbeiderpartiet",
    "H": "Høyre",
    "Frp": "Fremskrittspartiet",
    "FrP": "Fremskrittspartiet",
    "Sp": "Senterpartiet",
    "SV": "Sosialistisk Venstreparti",
    "V": "Venstre",
    "KrF": "Kristelig Folkeparti",
    "MdG": "Miljøpartiet de Grønne",
    "R": "Rødt"
}

SPEAKER_ROLE_TAG = {
    "statsminister": "Staatsminister",
    "statsministeren": "Staatsminister",
    "utenriksminister": "Außenminister",
    "utenriksministeren": "Außenminister",
    "president": "Präsident",
    "presidenten": "Präsident",
    "stortingspresident": "Präsident",
    "møteleder": "Vorsitzender",
    "møtelederen": "Vorsitzender",
    "statsråd": "Staatsrat",
    "statsrã¥d": "Staatsrat",
    "fung. leder": ""
}

PARLIAMENT = "Storting"
ISO3COUNTRY = "NOR"

# Use this president name if no other name is given on the HTML.
DEFAULT_PRESIDENT_NAME = "Olemic Thommessen"


def parse_norwegian_parliament_html(year_path: pathlib.Path,
                              year: int,
                              source_html_path: pathlib.Path,
                              meta_json_path: pathlib.Path):

    # Get parsed main text
    parsed_output = []

    # Open File
    file_name, response = open_file(source_html_path, meta_json_path)

    # Get president/leader mapping
    leader_president_mapping = create_leader_president_mapping(response)
    # Construct Date
    date = get_date(response)
    # Get Agenda Point
    try:
        agenda_paragraphs_ids, agenda_paragraphs = create_agenda(response)
    except AttributeError:
        print("No Agenda found!")
        return

    # Keep track of speeches
    speech_index = 1
    # Loop through agenda
    for agenda in agenda_paragraphs:

        # Find Sections
        speeches = agenda.find_all("div", attrs={'class': SECTION_HTML_TAG})
        agenda_title = agenda.find(attrs={'class': "strtngt_saktittel"})
        if agenda_title:
            agenda_title = agenda_title.get_text().strip()
            agenda_title = " ".join(agenda_title.split())
        else:
            if speech_index == 1:
                agenda_title = "Introduction"

        # Go through speeches
        for single_speeches in speeches:

            # Get Speaker and their political party
            speaker, speakerrole, party = get_speaker_speakerrole_party(single_speeches, leader_president_mapping)

            # If no speaker is not found, skip speech
            if speaker is None:
                continue

            # Get Paragraphs of speech
            paragraphs = single_speeches.find_all("p", attrs={'class': "strtngt_a"})

            # Go through paragraphs of speech
            for paragraphnumber, single_paragraph in enumerate(paragraphs):

                # Clean paragraph
                single_paragraph = clean_paragraph(single_paragraph)

                parsed_output.append(
                    {'date': date,
                     'agenda': agenda_title,
                     'speechnumber': speech_index,
                     'paragraphnumber': paragraphnumber+1,
                     'speaker': speaker,
                     'speakerrole': speakerrole,
                     'party': party,
                     'text': single_paragraph,
                     'parliament': "NO-" + PARLIAMENT,
                     'iso3country': ISO3COUNTRY
                     })

            speech_index += 1

        # Write parsed data
        path = year_path.joinpath(f"{file_name}_parsed.csv")
        write_csv(path, data=parsed_output,
                  fieldnames=['date', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'speakerrole','party',
                              'text', 'parliament', 'iso3country'])

def get_date(response):
    date = response.find('meta', attrs={'name': 'DC.Date'})["content"].strip('\t\n\r')
    locale.setlocale(locale.LC_TIME, 'no_NO')
    date = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

    return date

def get_speaker_speakerrole_party(single_section, president_mapping):
    speakerrole = None
    try:
        speaker = single_section.find("span", attrs={'class': 'strtngt_navn'}).getText()  # .split(":")[0]
        speaker = speaker.replace(":", "")
        speaker = speaker.replace("\n", " ")
        speaker = speaker.strip()
    except:
        return None, None, None

    # Get Political Party
    party = speaker[speaker.find("(") + 1:speaker.find(")")]
    if party in PARTY_MAPPING.keys():
        party = PARTY_MAPPING[party] + " (" + party + ")"
    else:
        party = None

    # Get Name of Speaker
    if speaker.lower() in president_mapping.keys():
        speaker_name = president_mapping[speaker.lower()]
        speaker = speaker.lower() + " " + speaker_name
    elif "(" in speaker:
        speaker = speaker.split("(")[0].strip()
    elif "[" in speaker:
        speaker = speaker.split("[")[0].strip()

    # Get Speaker Role
    potential_role = speaker.split(" ")[0].lower()
    if potential_role in SPEAKER_ROLE_TAG.keys():
        speakerrole = SPEAKER_ROLE_TAG[potential_role]
        speaker = " ".join(speaker.split(" ")[1:])

    return speaker, speakerrole, party

def clean_paragraph(single_paragraph):

    # Delete unwanted tags, e.g. name of speaker
    unwanted = single_paragraph.find('span')
    if unwanted:
        unwanted.extract()

    # Strip whitespaces beginning and end
    single_paragraph = single_paragraph.get_text().strip()

    # Clean everything in brackets
    single_paragraph = re.sub("[\(\[].*?[\)\]]", "", single_paragraph)

    single_paragraph = single_paragraph.replace(":", "")

    # Clean \n
    single_paragraph = single_paragraph.replace("\n", " ")

    # Strip whitespaces beginning and end
    single_paragraph = single_paragraph.strip()

    return single_paragraph


def create_leader_president_mapping(response):
    get_president = response.find('div', attrs={'class': 'large-7 large-offset-2 medium-8 columns'}).get_text()
    get_president = get_president.split("\n")
    name_president = None

    for str_president in get_president:
        str_president = str_president.strip("\r\t")
        if "President:" in str_president:
            name_president = "".join(str_president.split("President:")[1:]).strip()
        elif "Møteleder:" in str_president:
            name_president = "".join(str_president.split("Møteleder:")[1:]).strip()
    if not name_president:
        name_president = DEFAULT_PRESIDENT_NAME
    president_mapping = {"president": name_president,
                         "presidenten": name_president,
                         "møteleder": name_president,
                         "møtelederen": name_president,
                         "fung. leder": name_president}

    return president_mapping


def open_file(source_html_path, meta_json_path):
    # Get file name
    file_name = source_html_path.stem
    # Read meta data:
    meta_f = open(meta_json_path, 'r')
    meta_data = json.load(meta_f)
    # Get some meta data
    url = meta_data[file_name]['URL']
    print("Process: {url}".format(url=url))

    # Read source html
    f = codecs.open(source_html_path, 'r', 'utf-8')
    response = BeautifulSoup(f.read(), 'html.parser')

    return file_name, response

def create_agenda(response):
    # Get Agenda Point
    body = response.find("div", attrs={'class': "bigdoc-content"})
    find_potential_agenda = body.find_all("div", attrs={'id': re.compile("^m\d+$")})
    agenda_paragraphs = []
    agenda_paragraphs_ids = []
    for i in find_potential_agenda:
        if i['id'] in agenda_paragraphs_ids:
            continue
        agenda_paragraphs.append(i)
        agenda_paragraphs_ids.append(i['id'])

    return agenda_paragraphs_ids, agenda_paragraphs
