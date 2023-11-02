import pathlib
import re
from typing import Union, List
import json
import csv
import codecs
import unicodedata
import pandas as pd


def prepare_folder_eu(data_path: pathlib.Path, uid: str, summary: str, full: str):
    folder = data_path.joinpath("eu")
    folder.mkdir(parents=True, exist_ok=True)
    folder.joinpath(uid).mkdir(parents=True, exist_ok=True)
    # Summary and full documents folder
    folder.joinpath(uid, summary).mkdir(parents=True, exist_ok=True)
    folder.joinpath(uid, full).mkdir(parents=True, exist_ok=True)
    # Source folder for original page
    folder.joinpath(uid, summary, 'source').mkdir(parents=True, exist_ok=True)
    folder.joinpath(uid, full, 'source').mkdir(parents=True, exist_ok=True)
    return folder


def prepare_folder_national(data_path: pathlib.Path, country: str, national="national"):
    folder = data_path.joinpath(national)
    folder.mkdir(parents=True, exist_ok=True)
    folder = folder.joinpath(country)
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(2009, 2022):
        subfolder = folder.joinpath(str(i))
        subfolder.mkdir(parents=True, exist_ok=True)
        subfolder = subfolder.joinpath('source')
        subfolder.mkdir(parents=True, exist_ok=True)
    return folder


def normalize_name(title: str, event_type: str, doc_type: str, number: str):
    # Get lower event type seperated by underscore (e.g. legislative_proposal)
    event_type_lower = event_type.lower()
    event_type_lower = "_".join(event_type_lower.split())

    # Build normalized title
    if number is None:
        number = '1'
    normalized_title = doc_type + "_" + event_type_lower + "_" + number

    return normalized_title


def write_txt(path: pathlib.Path, txt: Union[list, str]):
    with codecs.open(path, "w", encoding="utf-8") as file:
        if isinstance(txt, list):
            for line in txt:
                file.write(line + "\n")
        elif isinstance(txt, str):
            file.write(txt)
        else:
            raise NotImplementedError


def write_meta(path: pathlib.Path, meta: dict) -> None:
    with codecs.open(path, "w", encoding="utf-8") as file:
        if isinstance(meta, dict):
            file.write(json.dumps(meta))
        else:
            raise NotImplementedError


def write_source_doc(path, content) -> None:
    with open(path, "wb") as file:
        file.write(content)


def write_csv(path: pathlib.Path, data: List[dict], fieldnames: List[str]):
    with codecs.open(path, "w", encoding="utf-8") as file:
        if isinstance(data, list):
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        else:
            raise NotImplementedError


def normalize_string(string: str) -> str:
    # Get rid of newline
    string = string.replace('\n', '')
    # Get rid of leading and trailing spaces and leading ,.
    string = string.strip().lstrip(',. ')
    # Replace multiple whitespaces
    string = re.sub(' +', ' ', string)
    # Normalize the string
    string = unicodedata.normalize('NFKC', string)
    return string


def parse_url(partial_url: str):
    """Get full from partial url and extract text."""
    # intermediate exemplary output ['location.href=', '/oeil/popups/summary.do?id=1502466&t=e&l=en', '']
    return "https://oeil.secure.europarl.europa.eu" + partial_url.split("'")[1]


def get_parliament_name(country_name: str):
    folder = 'config'
    filename = 'country_data.json'
    path = pathlib.Path(__file__).absolute().parent.parent.joinpath(folder, filename)
    # Read json
    with open(path) as f:
        data = json.load(f)
    attrs = data[country_name.capitalize()]
    return attrs['parliament_name']


def get_iso_2_digit_code(country_name: str):
    folder = 'config'
    filename = 'country_data.json'
    path = pathlib.Path(__file__).absolute().parent.parent.joinpath(folder, filename)
    # Read json
    with open(path) as f:
        data = json.load(f)
    attrs = data[country_name.capitalize()]
    return attrs['iso_2_digits']


def get_iso_3_digit_code(country_name: str):
    folder = 'config'
    filename = 'country_data.json'
    path = pathlib.Path(__file__).absolute().parent.parent.joinpath(folder, filename)
    # Read json
    with open(path) as f:
        data = json.load(f)
    attrs = data[country_name.capitalize()]
    return attrs['iso_3_digits']


def get_fieldnames():
    ''' Returns list of fields '''
    folder = 'config'
    filename = 'fieldnames.json'
    path = pathlib.Path(__file__).absolute().parent.parent.joinpath(folder, filename)
    # Read json
    with open(path) as f:
        data = json.load(f)

    keys = []
    for key, value in data.items():
        keys.append(key)
    return keys
