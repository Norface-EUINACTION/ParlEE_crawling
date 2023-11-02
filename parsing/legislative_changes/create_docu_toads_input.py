import pandas as pd
import pathlib
from bs4 import BeautifulSoup
import re
from eia_crawling.parsing.parsing_eu_proposal import parse_eu_proposal_not_formatted, parse_eu_proposal_formatted
from eia_crawling.parsing.parsing_eu_final_act_full import parse_eu_final_act_full
import pickle
from eia_crawling.spiders.utils import write_csv, normalize_string
import string

SPIDERS = 'spiders'
DATA = 'data'
ORIGIN = 'eu'
ENCODING = 'utf8'

OPENING_PHRASE = re.compile(
    r'.*((HAS|HAVE)\s*ADOPTED|(HAS|HAVE)\s*DECIDED|HAS\s*HAVE\s*ADOPTED)|HAS\s*Ö\s*HAVE\s*Õ\s*ADOPTED.*')

# Path to raw data
ROOT_PATH = pathlib.Path(__file__).absolute().parent.parent.parent.joinpath(SPIDERS, DATA, ORIGIN)

# Load annotations
# Annotation file for document identification
ANNOTATION = pd.read_csv(
    pathlib.Path(__file__).absolute().parent.joinpath('annotations', 'final_act_proposal_annotations.csv'))

# Documents to be skipped (for example due to bad download)
EXCLUDE = [ROOT_PATH.joinpath('2016/0380(COD)/full/source/full_legislative_proposal_1.html')]

OUTPUT_PATH = pathlib.Path(__file__).absolute().parent.joinpath('docu_toads_input', 'input').with_suffix('.txt')

def clean_text(text: str):
    printable = set(string.printable)
    text = ''.join(filter(lambda x: x in printable, text))
    return normalize_string(text)

def get_indices(parsed_document: list):
    indices = {}
    k = 0
    for i in range(len(parsed_document)):
        art_no = i + 1
        text_list = parsed_document[i]['text'].split()
        text_indices = [j + k + 1 for j in range(len(text_list))]
        indices[art_no] = text_indices
        k = text_indices[-1]
    return indices

def convert_to_docutoads(articles: list):
    text = " ".join([art['text'] for art in articles])
    text = clean_text(text)
    text_indices = get_indices(articles)
    art_list = [str(art['art_no']) for art in articles]
    return text, text_indices, art_list

def filter_empty_text(articles: list):
    return [x for x in articles if not x['text'] == '']


def parse_doc_pair(proposal_path: pathlib.Path, full_act_path: pathlib.Path):

    ### Parsing proposal ###
    # Convert .html to Beautiful Soup object
    soup = BeautifulSoup(open(str(proposal_path), encoding=ENCODING), "html.parser")

    # Depending on whether proposal doc is somewhat formatted or not, different parsing methods are used. Thus, first
    # one must check that. Non-formatted document is one that contains tags of following class: 'contentWrapper'.
    tag = soup.find('div', {'class': 'contentWrapper'})
    if tag is None:
        formatted = 0
    else:
        formatted = 1

    # Check whether the document has an opening phrase, if not that indicates lack of articles
    if soup.find(text=OPENING_PHRASE, recursive=True) is not None:
        has_articles = 1
    else:
        has_articles = 0

    # Calling two different parsing functions depending on value of 'formatted' variable
    if has_articles == 1:
        if formatted == 0:
            proposal_articles = parse_eu_proposal_not_formatted(proposal_path.parent, 'full_legislative_proposal_1')
            proposal_articles = filter_empty_text(proposal_articles)

            # Convert to DocuToads format
            proposal_text, proposal_indices, proposal_art_list = convert_to_docutoads(proposal_articles)

            # Save the text in the dir od original document
            proposal_text_path = proposal_path.parent.joinpath('full_legislative_proposal_1.txt')
            with open(str(proposal_text_path), 'w', encoding="utf-8") as f:
                f.write(proposal_text)

        else:
            proposal_articles = parse_eu_proposal_formatted(proposal_path.parent, 'full_legislative_proposal_1')
            proposal_articles = filter_empty_text(proposal_articles)

            # Convert to DocuToads format
            proposal_text, proposal_indices, proposal_art_list = convert_to_docutoads(proposal_articles)

            # Save the text in the dir od original document
            proposal_text_path = proposal_path.parent.joinpath('full_legislative_proposal_1.txt')
            with open(str(proposal_text_path), 'w', encoding="utf-8") as f:
                f.write(proposal_text)
    else:
        return None

    ### Parsing final act ###
    final_act_articles = parse_eu_final_act_full(full_act_path.parent, 'full_final_act_1')
    final_act_articles = filter_empty_text(final_act_articles)

    # Convert to DocuToads format
    final_act_text, final_act_indices, final_act_art_list = convert_to_docutoads(final_act_articles)

    # Save the text in the dir od original document
    final_act_text_path = proposal_path.parent.joinpath('full_final_act_1.txt')
    with open(str(final_act_text_path), 'w', encoding="utf-8") as f:
        f.write(final_act_text)

    # Return list
    return [str(proposal_text_path),
            str(final_act_text_path),
            'proposal',
            'final_act',
            proposal_art_list,
            final_act_art_list,
            proposal_indices,
            final_act_indices]


def main():
    """
    Iterates over documents and returns caselist required by DocuToads (see DocuToads documentation)
    """
    caselist = []
    for year in ROOT_PATH.iterdir():
        for cod in year.iterdir():
            if ((ANNOTATION['doc_key'] == ''.join([year.stem, cod.stem])) & (ANNOTATION['annot_final_act'] == 0) & (
                    ANNOTATION['annot_proposal'] == 0)).any():
                # Hard-coded exception
                if year.stem == '2011' and cod.stem == '0153(COD)':
                    continue

                proposal_path = cod.joinpath('full', 'source').joinpath('full_legislative_proposal_1.html')
                full_act_path = cod.joinpath('full', 'source').joinpath('full_final_act_1.html')
                if full_act_path.exists() and proposal_path.exists() and proposal_path not in EXCLUDE:
                    result = parse_doc_pair(proposal_path, full_act_path)
                    if result is not None:
                        result = result[:4] + [''.join([year.stem, cod.stem])] + result[4:]
                        caselist.append(result)

    # Pickling list object
    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(caselist, f, protocol=2)


if __name__ == "__main__":
    main()
