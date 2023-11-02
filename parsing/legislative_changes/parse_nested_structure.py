import pandas as pd
import pathlib
from bs4 import BeautifulSoup
import re
from eia_crawling.spiders.utils import write_csv, normalize_string
from argparse import ArgumentParser

SPIDERS = 'spiders'
DATA = 'data'
ORIGIN = 'eu'
ENCODING = 'utf8'
ROOT_PATH = pathlib.Path(__file__).absolute().parent.parent.parent.joinpath(SPIDERS, DATA, ORIGIN)

# Annotation file for document identification
ANNOTATION = pd.read_csv(
    pathlib.Path(__file__).absolute().parent.joinpath('annotations', 'final_act_proposal_annotations.csv'))

# Hard-coded patterns
OPENING_PHRASE = re.compile(
    r'\s*((HAS|HAVE)\s*ADOPTED|(HAS|HAVE)\s*DECIDED|HAS\s*HAVE\s*ADOPTED)|HAS\s*Ö\s*HAVE\s*Õ\s*ADOPTED.*')
CLOSING_PHRASE = re.compile(r'Done\s+at')
KEY_WORDS = ['replaced', 'inserted', 'deleted', 'amended', 'added', 'amending', 'numbered', 'renumbered']
END_QUOTATIONS = ('”', '"', '’', '’;', '".', "'", "';", "'.", '’.', 'ʼ', '”;', '”.', '”.', '"*', 'ˮ', '";', "'; and",
                  '’;')  # huge inconsistency, other characters might occur immediately afterwards
START_QUOTATIONS = re.compile(r'^ʻ|“|"|‘|(\')')
MIN_TEXT_LENGTH = 150


def getText(parent):
    return ''.join(parent.find_all(text=True, recursive=False)).strip()


def extract_change(doc_name: str, year: pathlib.Path, cod: pathlib.Path):
    """
    This function parses legislative changes which are listed in documents in a form of articles or article subpoints.
    Documents of such structure are identified with help of the annotation file located in
    /eia-crawling/eia_crawling/parsing/legislative_changes/annotations directory. Both final acts and proposals can be
    parsed. The extraction of changes is based on regex expression, as we noticed that a single amendment is typically preceded
    by one of following key words: "replaced", "inserted", "deleted", "amended", "added", "amending". Stems are not used,
    as experiments showed irrelevant text was retrieved. The key word should be then followed by colon and quotation mark
    or its different variations, such as ", ', '' and many more. Unfortunately, their use is not consistent across
    documents and sometimes not even within the same document. Regex expression are used for their identification. Text
    retrieved from a single tag has to be of a minimum length=MIN_TEXT_LENGTH, which was empirically set to 150
    The purpose of that was to discard tags with irrelevant texts. Its value can be changed in the future.

    To sum up, we define change as a following sequence:

    KEY_WORD: SOME_QUOTATION_MARK TEXT SOME_QUOTATION_MARK
    e.g.
    inserted: " this regulation shall apply to online intermediation services "

    :return: List of changes for a single document pair (final act & proposal): lst
    """

    changes = []  # list to be filled with instances of legislative change for a single document (final act)

    # Check if it's hard case; the document needs to be annotated with value= 1
    if doc_name == "full_final_act_1":
        if_hard_case = ((ANNOTATION['doc_key'] == ''.join([year.stem, cod.stem])) & ANNOTATION['annot_final_act'] == 1).any()

    elif doc_name == "full_legislative_proposal_1":
        if_hard_case = ((ANNOTATION['doc_key'] == ''.join([year.stem, cod.stem])) & ANNOTATION['annot_proposal'] == 1).any()
    else:
        raise ValueError('You are trying to use parser for unimplemented document type.')

    if if_hard_case:
        doc_path = cod.joinpath('full', 'source').joinpath(doc_name).with_suffix('.html')

        if doc_path.exists():
            soup = BeautifulSoup(open(str(doc_path), encoding=ENCODING), "html.parser")
            texts = []
            all_tags = soup.findAll(re.compile(r'.*'))  # Get all tags from HTTP document

            # Extract all texts inside tags
            for tag in all_tags:
                text = getText(tag)
                if len(text) > 0:
                    texts.append(text)

            # TEXT CLEANING: Note that a piece of text extracted from HTML can be spread across different tags,
            # i.e. siblings, children, etc. It the case of final acts following unwanted pattern has been detected:
            # article or sub-article numbers that are surrounded by parentheses occur in different tag than the text,
            # thus they must be join with the respective text, e.g. two consecutive tags:
            # <p> (1)
            # <p> the appropriate section of the accompanying animal health certificate;
            # must be extracted as concatenated into:
            # (1) the appropriate section of the accompanying animal health certificate
            # Otherwise, we are not able to identify the number of an article.
            for i in range(len(texts)):
                if re.compile(r'^\(.*\)$').match(texts[i]):
                    texts[i + 1] = (' '.join([texts[i], texts[i + 1]]))

            # Find the index of opening phrase, start parsing from there
            opening = [m for m, item in enumerate(texts) if re.search(OPENING_PHRASE, item)][0]

            if opening is None:
                print(
                    "Opening phrase not detected: Please update the regex expression or check validity of document")

            else:
                texts = texts[opening + 1:]
                for i in range(len(texts)):

                    # Stop parsing when closing phrase is found
                    if CLOSING_PHRASE.match(texts[i]):
                        break

                    # Find the regex pattern: find beginning and end of a single change
                    for word in KEY_WORDS:
                        if word in texts[i] and re.compile(r'^(\(.*\)|\d|[a-z]\)|–)|(In)\s+following:').match(
                                texts[i]) and len(texts[i]) < MIN_TEXT_LENGTH and 'added tax' not in texts[i]:

                            if START_QUOTATIONS.match(texts[i + 1].strip()):
                                change = texts[i + 1]

                                j = i
                                while not change.rstrip().endswith(END_QUOTATIONS):
                                    new_change = texts[j + 1]
                                    change = ' '.join([change, new_change])
                                    j += 1

                            else:
                                change = ''

                            changes.append(
                                (year.stem, cod.stem, 'final_act', normalize_string(texts[i]),
                                 normalize_string(change)))
    return changes


def main(doc_name: str):
    """
    Iterate over all documents of certain type
    :return: csv file: /eia-crawling/eia_crawling/parsing/legislative_changes/hard_cases.csv
    """
    changes = []  # list to be filled with instances of legislative change for all final acts identified as hard cases

    for year in ROOT_PATH.iterdir():  # Iterate over all years and cods to identify hard cases
        print(f"Parsing {year.stem} year ({doc_name})")
        for cod in year.iterdir():
            changes += extract_change(doc_name, year, cod)

    df = pd.DataFrame(changes, columns=['year', 'cod', 'doc_type', 'change_type', 'change_text'])
    df.to_csv(pathlib.Path(__file__).absolute().parent.joinpath('outputs', 'nested', doc_name, 'nested_structure_changes.csv'))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("doc_name", type=str,
                        help="Choose one of: [full_final_act_1, full_legislative_proposal_1]")
    args = parser.parse_args()
    doc_name = args.doc_name
    main(doc_name=doc_name)
