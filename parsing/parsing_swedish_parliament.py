import pathlib
import re
import datetime
from bs4 import BeautifulSoup
from eia_crawling.spiders.utils import get_parliament_name, get_iso_2_digit_code, get_iso_3_digit_code, write_csv, \
    normalize_string

COUNTRY = 'sweeden'
ENCODING = 'utf8'
MONTHS = {"januari": 1, "februari": 2, "mars": 3, "april": 4, "maj": 5, "juni": 6, "juli": 7, "augusti": 8,
          "september": 9, "oktober": 10, "november": 11, "december": 12}

PARTIES = ['S', 'M', 'SD', 'C', 'V', 'KD', 'L', 'MP']


def get_date(path_to_file: pathlib):
    year = int(path_to_file.parent.parent.stem)
    file_name = path_to_file.stem
    date_rgx = re.split("Protokoll\s+\d{4}_\d{2}_\d{0,3}", file_name)[1].split()
    day = int(date_rgx[2])
    month = MONTHS[date_rgx[3]]

    return datetime.date(year, month, day).strftime('%Y-%m-%d')


def get_speech(start_tag):
    next_tag = start_tag.find_next_sibling()

    text_tags = []
    while next_tag is not None:
        if next_tag.name not in ['h1', 'h2']:
            text_tags.append(next_tag)
            next_tag = next_tag.find_next_sibling()
        else:
            break

    paragraphs = []
    agenda_point = ''

    for tag in text_tags:
        # Get paragraphs
        if tag.attrs.__contains__('class'):
            if tag['class'][0] == 'NormalIndent' and len(tag.get_text().strip()) > 0:
                paragraphs.append(tag.get_text())

        # Get floating agenda point if exists
        if tag.name == 'div' and tag.attrs.__contains__('style'):
            rubric = tag.find('p', {"class": "Kantrubrik"})
            if rubric is not None and not len(agenda_point) > 0:
                agenda_point = rubric.get_text().strip()

    return agenda_point, paragraphs


def get_first_agenda_point(soup_object):
    ag_tags = soup_object.findAll('p', {'class': 'Kantrubrik'})
    current_agenda = [ag_tag for ag_tag in ag_tags if len(ag_tag.get_text().strip()) > 0][0]
    return current_agenda.get_text()


def get_speaker_data(start_tag):
    party = ''  # not available when speaker holds a function
    text = start_tag.get_text()
    text = text.replace('Anf.', '').replace(':', '')
    lst = re.findall(r"\b[A-ZÅÄÖ\-]+\b", text)
    name = ' '.join([x for x in lst if x not in PARTIES])
    # Format name
    name = ' '.join([w.lower().capitalize() for w in name.split()])
    name = re.sub("-\s*([a-zA-Z])", lambda p: p.group(0).upper(), name)
    if lst[-1] in PARTIES:
        party = lst[-1]
    return name, party


def parse_swedish_parliament(source_html_path: pathlib,
                             year_path: pathlib.Path,
                             year: int):
    # Convert document into Beautiful Soup object
    soup = BeautifulSoup(open(str(source_html_path), encoding=ENCODING), "html.parser")
    speech_tags = soup.findAll('h2')
    speech_tags = [tag for tag in speech_tags if not tag.attrs.__contains__('class')]

    # Check if document contains speeches (if parsable)
    if_parsable = soup.find(text=re.compile('Anf.'))

    if if_parsable:

        # Get date
        date = get_date(source_html_path)

        # Read parliament name and ISO codes
        parliament_name = get_parliament_name(COUNTRY)
        iso_2_digits = get_iso_2_digit_code(COUNTRY)
        iso_3_digits = get_iso_3_digit_code(COUNTRY)

        # Get first agenda point (floating object so it is not guaranteed it will appear in first speech tag)
        current_agenda_point = get_first_agenda_point(soup)

        list_of_dicts = []
        speech_no = 1
        # Parse speech tags
        for tag in speech_tags:
            name, party = get_speaker_data(tag)
            agenda_point, paragraphs = get_speech(tag)
            if len(agenda_point) > 0:
                current_agenda_point = agenda_point

            paragraph_no = 1
            for p in paragraphs:
                list_of_dicts.append({
                    "date": date,
                    "parliament": iso_2_digits + '-' + parliament_name,
                    "iso3country": iso_3_digits,
                    "speaker": name,
                    "party": party,
                    "speechnumber": speech_no,
                    "paragraphnumber": paragraph_no,
                    "agenda": current_agenda_point,
                    "text": normalize_string(p)
                })
                paragraph_no += 1
            speech_no += 1

        # Save data
        file_name = source_html_path.stem
        path = year_path.joinpath(f"{file_name}_parsed.csv")
        write_csv(path, data=list_of_dicts,
                  fieldnames=['date', 'parliament', 'iso3country', 'speaker', 'party', 'speechnumber',
                              'paragraphnumber', 'agenda', 'text'])
    else:
        print(source_html_path)
