import pathlib
import datetime
from bs4 import BeautifulSoup
from eia_crawling.spiders.utils import get_parliament_name, get_iso_2_digit_code, get_iso_3_digit_code, write_csv, normalize_string

COUNTRY = 'denmark'
ENCODING = 'utf8'

political_parties = {'V': 'Venstre, Danmarks Liberale Parti',
                     'S': 'Socialdemokratiet i Danmark',
                     'DF': 'Dansk Folkeparti',
                     'RV': 'Det Radikale Venstre',
                     'SF': 'Socialistisk Folkeparti',
                     'EL': 'Enhedslisten - De Rød-Grønne',
                     'KF': 'Det Konservative Folkeparti',
                     'A': 'Alternativet',
                     'ALT': 'Alternativet',
                     'NB': 'Nye Borgerlige',
                     'LA': 'Liberal Alliance',
                     'KD': 'Kristendemokraterne'
                     }


def parse_danish_parliament(source_html_path: pathlib,
                            year_path: pathlib.Path,
                            year: int):
    def get_agenda_name(agenda_tag):
        name = agenda_tag.find_next_sibling('meta', {'name': 'ShortTitle'})['content']
        return name

    def get_speaker_tags_per_agenda(agenda_tag):
        # Get all speaker tags AFTER agenda tag and tags that separate agenda points ('hr')
        siblings = agenda_tag.find_next_siblings(lambda tt: tt.name == 'hr' or (
                tt.name == 'meta' and 'name' in tt.attrs and tt.attrs['name'] == 'Start MetaSpeakerMP'))

        # Get the indexes of all separating tag
        idxes = [idx for idx, element in enumerate(siblings) if element.name == 'hr']

        # Return sliced siblings so that siblings belonging to further agenda points are removed
        return siblings[0:idxes[0]]

    def get_speaker_meta_data(speaker_tag):
        # Get first name of the Speaker
        first_name_tag = speaker_tag.find_next_sibling().find_next_sibling()
        first_name = first_name_tag['content']

        # Get second name of the Speaker
        second_name_tag = first_name_tag.find_next_sibling()
        second_name = second_name_tag['content']

        # Get group name short
        party_tag = second_name_tag.find_next_sibling()
        party = party_tag['content']
        party_full_name = ''
        try:
            party_full_name = political_parties[party]
        except KeyError:
            pass

        # Get role of the Speaker
        role_tag = party_tag.find_next_sibling()
        role = role_tag['content']

        return {'first_name': first_name, 'second_name': second_name, 'party_abbreviation': party,
                'party_full_name': party_full_name, 'role': role}

    ###### Here starts actual parsing with the help of above functions ######

    # Get filename
    file_name = source_html_path.stem

    # Read parliament name and ISO codes
    parliament_name = get_parliament_name("denmark")
    iso_2_digits = get_iso_2_digit_code("denmark")
    iso_3_digits = get_iso_3_digit_code("denmark")

    # Convert document into Beautiful Soup object
    soup = BeautifulSoup(open(str(source_html_path), encoding=ENCODING), "html.parser")

    # Parse the date
    date = soup.find('meta', {'name': 'DateOfSitting'})['content']
    date = datetime.datetime.fromisoformat(date)
    date = date.replace(hour=0, minute=0, second=0)

    # # Initialize list for paragraphs
    list_of_dct = []

    # Retrieve all Agenda tags
    agenda_tags = soup.findAll('meta', {'name': 'Start MetaFTAgendaItem'})

    # Initiate speeches numeration
    i = 1
    for a_tag in agenda_tags:
        # Get Agenda name
        agenda_name = get_agenda_name(a_tag)

        # Get Speaker start tags for the Agenda point
        speaker_tags = get_speaker_tags_per_agenda(a_tag)

        # Retrieve paragraphs per each Speaker
        for s_tag in speaker_tags:
            j = 1
            # Get Speaker meta data
            speaker_meta_data = get_speaker_meta_data(s_tag)

            # Find the tag that starts a speech
            speech_start_tag = s_tag.find_next_sibling('meta', {'name': 'End MetaSpeechSegment'})
            text_tag_names = ['Tekst', 'TekstIndryk', 'TekstLuft']

            # Get all the text from these tags up to tag 'p, {'class':'Tid'}
            text_tag = speech_start_tag

            if speaker_meta_data['first_name'] != 'MødeSlut' and agenda_name != 'Punkt 0':
                while text_tag.find_next_sibling() is not None:

                    has_class = text_tag.find_next_sibling().attrs.__contains__('class')

                    if has_class and text_tag.find_next_sibling()['class'][0] in text_tag_names:
                        next_tag = text_tag.find_next_sibling()
                        paragraph = next_tag.get_text()
                        paragraph = normalize_string(paragraph)
                        dct = {"parliament": parliament_name,
                               "iso2country": iso_2_digits,
                               "iso3country": iso_3_digits,
                               "date": date,
                               "agenda": agenda_name,
                               "speechnumber": i,
                               "speaker_first_name": speaker_meta_data['first_name'],
                               "speaker_last_name": speaker_meta_data['second_name'],
                               "speaker": speaker_meta_data['first_name'] + " " + speaker_meta_data['second_name'],
                               "speakerrole": speaker_meta_data['role'],
                               "party_abbreviation": speaker_meta_data['party_abbreviation'],
                               "party": speaker_meta_data['party_full_name'],
                               "paragraphnumber": j,
                               "text": paragraph
                               }
                        list_of_dct.append(dct)
                        text_tag = text_tag.find_next_sibling()
                        j += 1
                    else:
                        break
            i += 1

    # Write parsed document
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path,
              data=list_of_dct,
              fieldnames=['parliament', 'iso2country', 'iso3country', 'date', 'agenda', 'speechnumber',
                          'speaker_first_name', 'speaker_last_name', 'speaker', 'speakerrole', 'party_abbreviation', 'party',
                          'paragraphnumber', 'text'])

