import pathlib
import datetime
from bs4 import BeautifulSoup
from eia_crawling.spiders.utils import get_parliament_name, get_iso_2_digit_code, get_iso_3_digit_code, write_csv, \
    normalize_string
import re
import functools as ft

COUNTRY = 'hungary'
ENCODING = 'utf8'

# List of Hungarian parties active between 2009-2019
hungarian_parties = ['DKP', 'DEMP', 'MDF', 'SZDSZ', 'SZKT', 'MDNP', 'HP', '4K!', 'Együtt', 'ÖP', 'MoMa', 'Fidesz',
                     'KDNP', 'Jobbik', 'MSZP', 'DK', 'LMP', 'Párbeszéd', 'Momentum', 'Mi Hazánk', 'PV', 'ISZOMM',
                     'Liberálisok', 'ÚK']

# Hard-coded text for look-up
OPENING_PHRASE = 'A felszólalás szövege'
CLOSING_PHRASES = ['Az ülésnapot bezárom', 'Az ülést bezárom']


def parse_hungarian_parliament(source_html_path: pathlib,
                               year_path: pathlib.Path,
                               year: int):

    ###### Find below a set of helper functions ######

    def retrieve_from_brackets(text: str):
        """
        Retrieving text embedded in rounded brackets, eg. (Fidesz)
        """
        retrieved_text = ''
        for char in text:
            if char == '(' or char == ')':
                pass
            else:
                retrieved_text += char
        return retrieved_text

    def get_name(speaker_data: str):
        """
        Retrieve the name of the Speaker from the initial part of the text.

        Logic: 1) full name longer than 2 words,
               2) upper-cased,
               3) leading word has more than 1 character,
               4) word not embedded in bracket to avoid getting party name
        """

        name_string = []
        t = speaker_data.split()

        if t[0].isupper() and len(t[0]) > 1:
            for token in t:
                if token.isupper() and re.match(r"^\(", token) is None and len(token) > 1:
                    name_string.append(token)
                else:
                    break

        name = ' '.join(name_string)
        # Remove 'DR.' from name
        name = name.replace('DR.', '').strip()
        # Make sure it's a name (2 or more words are accepted with the exception of 'ELNÖK')
        if (len(list(name.split())) <= 1 and name != 'ELNÖK') or name == '„M25 MOST”':
            name = ''
        return name

    def get_party_and_role(speaker_data: str):
        """
        Retrieve information about the party
        Logic: 1) embedded in rounded brackets (_)
               or
               2) embedded in text preceding the name

        Retrieve information about the role
        Logic: 1) text preceding the name
               2) text does not contain party name and 'képviselőcsoportja részéről'
        """

        name = get_name(speaker_data)

        # Get party if written in brackets
        try:
            party_brackets = re.findall(r'\(.*?\)', speaker_data)[0]
            party = retrieve_from_brackets(party_brackets).strip()
        except IndexError:
            party = ''

        # Get role
        if party == '':
            try:
                end_name_word = name.split()[-1]  # localize last word from name
                role = speaker_data.split(end_name_word, 1)[1].strip()
            except IndexError:
                role = ''
        else:
            role = ''

        # Get party if embedded in text
        for token in role.split():
            if token in hungarian_parties and party == '':
                party = token
                role = ''
        return party, role

    def get_speaker_data(paragraph: str):
        """
        Retrieves part of the text containing speaker data:
        Handles two types of text splits:
            1. Case --> {NAME} {data about party & role} : text
            2. Case --> {NAME} {data about party & role} . text
        Aggregates speaker data into one dictionary that is later used when retrieving paragraphs' texts.
        """
        # Try to split the string by ':'
        split = paragraph.split(':', 1)  # Here 1 means at most 1 split is done
        speaker_data = split[0]

        # Edge case: No ':' sign after speaker info, '.' sign instead
        if get_name(speaker_data) != '' and len(split) == 1:
            speaker_data = paragraph.split('.', 1)[0]

        # Remove ',' sign
        speaker_data = speaker_data.replace(',', '')

        # Get name of Speaker
        name = get_name(speaker_data)

        # Get party membership and role
        party, role = get_party_and_role(speaker_data)

        speaker_meta_data = {'name': name, 'role': role, 'party': party}
        return speaker_meta_data

    ###### Here starts actual parsing with the help of above functions ######
    # Get filename
    file_name = source_html_path.stem

    # Retrieve date from a filename
    file_name_tokens = file_name.split()
    date = file_name_tokens[2]
    date = date.replace('(', '').replace(')', '')
    date = datetime.datetime.strptime(date, '%Y.%m.%d.')
    date = date.replace(hour=0, minute=0, second=0)

    # Convert document into Beautiful Soup object
    soup = BeautifulSoup(open(str(source_html_path), encoding=ENCODING), "html.parser")

    # Read parliament name and ISO codes
    parliament_name = get_parliament_name(COUNTRY)
    iso_2_digits = get_iso_2_digit_code(COUNTRY)
    iso_3_digits = get_iso_3_digit_code(COUNTRY)

    # Initialize list of dictionaries -> list of paragraphs
    list_of_dct = []

    # Find start tag
    try:
        start_tag = soup.find('h3', text=re.compile(OPENING_PHRASE))

        # Identify sibling paragraphs
        siblings = start_tag.find_next_siblings()
        i = 0
        j = 0

        # Initiate speaker data that will be reset every time new speaker has voice
        current_name = ''
        current_party = ''
        current_role = ''

        for sibling in siblings:
            paragraph_nodes = sibling.findAll(text=True)
            paragraph_text = ' '.join([t for t in paragraph_nodes if t])
            paragraph_text = normalize_string(paragraph_text)

            # Stop retrieving other tags if parliament sitting was announced to be closed
            if any(phrase in paragraph_text for phrase in CLOSING_PHRASES):
                break

            # Assign each paragraph to a person
            if paragraph_text != '':
                speaker_data = get_speaker_data(paragraph_text)
                if speaker_data['name'] == '':
                    j += 1
                else:  # Here changing the speaker data for opening paragraph
                    current_party = speaker_data['party']
                    current_role = speaker_data['role']
                    current_name = speaker_data['name']

                    # Edge case: If text comes after '.' sign in opening paragraph, adjust it
                    try:
                        paragraph_text = paragraph_text.split(':', 1)[1].strip()
                    except IndexError:
                        paragraph_text = paragraph_text.split('.', 1)[1].strip()

                    j = 1
                    i += 1
                    # Get rid of paragraphs that contain only time information, return dct for all others
                if not re.match(r'^\(.*?\)$', paragraph_text):
                    dct = {'parliament': iso_2_digits + '-' + parliament_name,
                           'iso3country': iso_3_digits,
                           'date': date,
                           'speaker': current_name,
                           'party': current_party,
                           'speakerrole': current_role,
                           'speechnumber': i,
                           'paragraphnumber': j,
                           'text': paragraph_text}

                    # print(dct)
                    list_of_dct.append(dct)
            else:
                pass

        # Write parsed document
        path = year_path.joinpath(f"{file_name}_parsed.csv")
        write_csv(path,
                  data=list_of_dct,
                  fieldnames=['parliament', 'iso3country', 'date', 'speaker', 'party',
                              'speakerrole', 'speechnumber', 'paragraphnumber', 'text'])
    except AttributeError:
        print(f'File not found: {file_name}')

#### Testing
# path = pathlib.Path(
#    'C:/Users/48668\Downloads/2011/source/139. ülésnap (2011.11.22. ) összefoglaló.html')
# year_path = pathlib.Path('C:/Users/48668/Downloads/2011')
# parse_hungarian_parliament(path, year_path, 2011)
