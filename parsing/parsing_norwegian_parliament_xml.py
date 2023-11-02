import json
import pathlib
import unicodedata
import csv
import sys
import datetime
from bs4 import BeautifulSoup
import os
import re
from eia_crawling.spiders.utils import write_csv
import codecs
from codecs import EncodedFile

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
    "MDG": "Miljøpartiet De Grønne",
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


def parse_norwegian_parliament_xml(year_path: pathlib.Path,
                                   year: int,
                                   source_xml_path: pathlib.Path):
    # Read the XML file
    with open(source_xml_path, "r", encoding="utf-8") as file:
        # Read each line in the file, readlines() returns a list of lines
        content = file.readlines()
        # Combine the lines in the list into a string
        content = "".join(content)
        response = BeautifulSoup(content, "lxml")

    print("Parse: {}".format(source_xml_path))

    # Get parsed main text
    parsed_output = []

    # Construct Date
    date = get_date(source_xml_path)

    # Get president/leader mapping
    leader_president_mapping = create_leader_president_mapping(response)

    # Get Agenda Point
    agenda_paragraphs = create_agenda(response)

    # Keep track of speeches
    speech_index = 1
    # Loop through agenda
    for agenda in agenda_paragraphs:

        agenda_title = get_agenda_title(agenda)

        # Get speeches
        speeches_children = get_speeches(agenda)
        if not speeches_children:
            continue

        # Go through speeches
        for speech in speeches_children:
            if speech.name == "sakshode" or speech.name == "tit" or speech.name == "refspm"\
                    or speech.name == "dagsorden" or speech.name == "dato" or speech.name == "president" \
                    or speech.name == "subtit" or not speech.name:
                continue

            # Get Speaker and their political party
            speaker, speakerrole, party = get_speaker_speakerrole_party(speech, leader_president_mapping)

            # If no speaker is not found, skip speech
            if speaker is None:
                continue

            # Get Paragraphs of speech
            paragraphs = speech.find_all("a")

            # Go through paragraphs of speech
            for paragraphnumber, single_paragraph in enumerate(paragraphs):
                # Clean paragraph
                single_paragraph = clean_paragraph(single_paragraph)

                parsed_output.append(
                    {'date': date,
                     'agenda': agenda_title,
                     'speechnumber': speech_index,
                     'paragraphnumber': paragraphnumber + 1,
                     'speaker': speaker,
                     'speakerrole': speakerrole,
                     'party': party,
                     'text': single_paragraph,
                     'parliament': "NO-" + PARLIAMENT,
                     'iso3country': ISO3COUNTRY
                     })

            speech_index += 1

        # Write parsed data
        path = year_path.joinpath(f"{source_xml_path.stem}_parsed.csv")

        write_csv(path, data=parsed_output,
                  fieldnames=['date', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'speakerrole', 'party',
                              'text', 'parliament', 'iso3country'])

def get_date(source_xml_path):
    filename = os.path.basename(source_xml_path).split(".")[0]
    year = "20" + filename[1:3]
    month = filename[3:5]
    day = filename[5:7]

    date = datetime.datetime.strptime(year + "-" + month + "-" + day, '%Y-%m-%d')

    return date

def get_speeches(agenda):
    # Get speeches
    if agenda.find("sak"):
        speeches_children = agenda.find("sak").children
    elif agenda.find("sporretime"):
        speeches = agenda.find("sporretime")
        speeches_children = []

        for speech in speeches.children:
            if speech.name == "sakshode" or not speech.name:
                continue
            elif speech.name == "spm":
                add_speech = list(speech.children)
                speeches_children += add_speech
            else:
                speeches_children.append(speech)
    elif agenda.find("referat"):
        return None
    elif agenda.name == "formalia":
        speeches_children = agenda.children
    else:
        sys.exit("No Agenda found.")

    return speeches_children

def get_agenda_title(agenda):

    if agenda.name == "formalia":
        agenda_title = "Introduction"
    else:
        agenda_title = [part_title.get_text() for part_title in agenda.find_all("saktit")]
        agenda_title = " ".join(agenda_title)
        if agenda_title:
            agenda_title = agenda_title.strip()
        else:
            agenda_title = None
    return agenda_title

def get_speaker_speakerrole_party(speech, president_mapping):
    speakerrole = None
    speech_tag = speech.name
    if speech_tag == "presinnl":
        speaker = president_mapping["president"]
        speakerrole = "Präsident"
    elif speech_tag == "handling" or speech_tag == "votering":
        # TODO: Change of president?
        return None, None, None
    else:
        speaker = speech.find("navn").get_text()

    speaker = speaker.replace(":", "")
    speaker = speaker.replace("\n", " ")
    speaker = speaker.strip()

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
    name_president = response.find('president').get_text().strip("\n")

    president_mapping = {"president": name_president}

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
    agenda_paragraphs = []

    # Get Agenda Point
    agenda_paragraphs += response.find_all("formalia")
    agenda_paragraphs += response.find_all("saker")
    return agenda_paragraphs
