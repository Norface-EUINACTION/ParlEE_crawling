import pathlib
from bs4 import BeautifulSoup
import csv
import re
from parsing_eu_proposal import parse_eu_proposal_not_formatted, parse_eu_proposal_formatted
from parsing_eu_final_act_full import parse_eu_final_act_full

SPIDERS = 'spiders'
DATA = 'data'
ORIGIN = 'eu'
ENCODING = 'utf8'
OPENING_PHRASE = re.compile(
    r'.*((HAS|HAVE)\s*ADOPTED|(HAS|HAVE)\s*DECIDED|HAS\s*HAVE\s*ADOPTED)|HAS\s*Ö\s*HAVE\s*Õ\s*ADOPTED.*')
EMBED_VOCAB = ['insert', 'replac', 'delet', 'amend', 'add', 'number', 'renumber']
EMBED_VOCAB_RE = [re.compile(r'((is|are)\s*)?{}'.format(x)) for x in EMBED_VOCAB]

# Get the path to raw data
ROOT_PATH = pathlib.Path(__file__).absolute().parent.parent.joinpath(SPIDERS, DATA, ORIGIN)
EXCLUDE = [ROOT_PATH.joinpath('2016/0380(COD)/full/source/full_legislative_proposal_1.html')]

proposal_meta_data = []
proposal_data = []
final_act_meta_data = []
final_act_data = []

# Iterate over documents
for year in ROOT_PATH.iterdir():
    print(year.stem)
    for cod in year.iterdir():
        proposal_path = cod.joinpath('full', 'source').joinpath('full_legislative_proposal_1.html')
        full_act_path = cod.joinpath('full', 'source').joinpath('full_final_act_1.html')

        if proposal_path.exists() and proposal_path not in EXCLUDE:

            # Convert .html to Beautiful Soup object
            soup = BeautifulSoup(open(str(proposal_path), encoding=ENCODING), "html.parser")

            # Check if document is formatted
            formatted = 1
            has_articles = 1
            tag = soup.find('div', {'class': 'contentWrapper'})
            if tag is None:
                formatted = 0

                # Not formatted: Check if has opening phrase
                opening_tag = soup.find('p', text=OPENING_PHRASE)
                if opening_tag is None:
                    has_articles = 0

            else:
                # Formatted: Check if has opening phrase
                opening_tag = soup.find('p', {'class': 'Formuledadoption'})
                opening_tag_1 = soup.find('span', text=OPENING_PHRASE)
                if opening_tag is None and opening_tag_1 is None:
                    has_articles = 0

            # Attach no. of articles and occurrences of vocabulary typically present in docs with embedded Articles
            art_no = 0
            articles = None
            embedded_dct = dict.fromkeys(EMBED_VOCAB, 0)
            celex = None

            if has_articles == 1:  # Broken HTML, e.g Article 4223

                if formatted == 0:
                    articles = parse_eu_proposal_not_formatted(proposal_path.parent, 'full_legislative_proposal_1')
                else:
                    articles = parse_eu_proposal_formatted(proposal_path.parent, 'full_legislative_proposal_1')

                for art in articles:
                    proposal_data.append(art)

                art_no = len(articles)

                for art in articles:
                    for i in range(len(EMBED_VOCAB_RE)):
                        embedded_dct[EMBED_VOCAB[i]] += len(re.findall(EMBED_VOCAB_RE[i], art['text']))

                if len(articles) > 0:
                    celex = articles[0]['celex']
                else:
                    print(f'EXCEPTION {proposal_path}')

            dct = {'doc_name': 'full_legislative_proposal_1.html', 'year': year.stem, 'celex': celex, 'cod': cod.stem,
                   'formatted': formatted, 'has_articles': has_articles, 'no_of_main_articles': art_no}

            meta_dct = {**dct, **embedded_dct}
            proposal_meta_data.append(meta_dct)

        embedded_dct_final = dict.fromkeys(EMBED_VOCAB, 0)
        celex_final = None
        if full_act_path.exists():
            output = parse_eu_final_act_full(full_act_path.parent, 'full_final_act_1')
            output_len = len(output)
            for art in output:
                for i in range(len(EMBED_VOCAB_RE)):
                    embedded_dct_final[EMBED_VOCAB[i]] += len(re.findall(EMBED_VOCAB_RE[i], art['text']))

            if output_len > 0:
                celex_final = output[0]['celex']
            else:
                print(f'EXCEPTION {proposal_path}')

            dct_final = {'doc_name': 'full_final_act_1.html', 'year': year.stem, 'celex': celex_final, 'cod': cod.stem,
                         'no_of_main_articles': output_len}
            meta_final_dct = {**dct_final, **embedded_dct_final}
            final_act_meta_data.append(meta_final_dct)

output_meta_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('config').joinpath(
    'full_legislative_proposal_1_metadata.csv')
output_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('config').joinpath(
    'full_legislative_proposal_1.csv')
output_final_meta_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('config').joinpath(
    'full_final_act_metadata.csv')

# Meta information about each proposal
with open(output_meta_path, 'w', encoding=ENCODING, newline='') as output_file:
    fc = csv.DictWriter(output_file, fieldnames=proposal_meta_data[0].keys())
    fc.writeheader()
    fc.writerows(proposal_meta_data)
    print('Meta data written.')

# Parsed proposals
with open(output_path, 'w', encoding=ENCODING, newline='') as output_file:
    fc = csv.DictWriter(output_file, fieldnames=proposal_data[0].keys())
    fc.writeheader()
    fc.writerows(proposal_data)
    print('Parsed articles written.')

# Meta information about each final act
with open(output_final_meta_path, 'w', encoding=ENCODING, newline='') as output_file:
    fc = csv.DictWriter(output_file, fieldnames=final_act_meta_data[0].keys())
    fc.writeheader()
    fc.writerows(final_act_meta_data)
    print('Meta'
          ' data written.')