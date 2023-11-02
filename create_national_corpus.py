import numpy as np
import pathlib
from argparse import ArgumentParser
import codecs
import csv
import re
import stanza
import time
import datetime
from eia_crawling.spiders.utils import write_csv
import os
import sys

SOURCE = 'source'
SPIDERS = 'spiders'
DATA = 'data'
NATIONAL = 'national'
EIA = 'eia_crawling'
PARTY_POSITIONG = 'party_positioning'

maxInt = sys.maxsize

# Austrian data contained very large fields
# Following code line should fix this
while True:
    # decrease the maxInt value by factor 10
    # as long as the OverflowError occurs.

    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt / 10)


def main(country: str,
         language: str = None,
         num_paragraphs: int = None,
         gpu_id: str = None):
    """
    Merge all the single speeches files to a large corpus per country
    Split each row on sentence level, with Stanford stanza (GPU required)
    Prerequisites:
    - The crawler and parser for the specific country were executed.

    num_paragraphs: Parameter to limit the number of paragraphs that are splitted for debugging purposes
    """

    if gpu_id:
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id

    # Get the path to the national folder
    current_p = pathlib.Path(__file__).absolute().parent.parent

    # Use this script to split EU speeches as well
    root_p = current_p.joinpath(EIA, SPIDERS, DATA, NATIONAL, country)

    # Default years:
    years = list(np.arange(2009, 2020))

    # Init the final corpus
    corpus = []
    # Set the path to write the corpus to
    if country == 'ep':
        corpus_p = current_p.joinpath(PARTY_POSITIONG, DATA, f"{country}_corpus_2009_2019_{language}.csv")
        if language == 'cy':
            lang = 'el'
        else:
            lang = language
    else:
        corpus_p = current_p.joinpath(PARTY_POSITIONG, DATA, f"{country}_corpus_2009_2019.csv")

    # Define a country specific settings for the corpus
    if country == 'ireland':
        lang = 'ga'
    elif country == 'united_kingdom':
        lang = 'en'
    elif country == 'germany' or country == 'austria':
        lang = 'de'
    elif country == 'hungary':
        lang = 'hu'
    elif country == 'denmark':
        lang = 'da'
    elif country == 'france' or country == 'belgium':
        lang = 'fr'
    elif country == 'czechia':
        lang = 'cs'
    elif country == 'spain':
        lang = 'es'
    elif country == 'finland':
        lang = 'fi'
    elif country == 'netherland':
        lang = 'nl'
    elif country == 'portugal':
        lang = 'pt'
    elif country == 'sweden':
        lang = 'sv'
    elif country == 'bulgaria':
        lang = 'bg'
    elif country == 'greece':
        lang = 'el'
    elif country == 'lithuania':
        lang = 'lt'
    elif country == 'slovenia':
        lang = 'sl'
    elif country == 'croatia':
        lang = 'hr'
    elif country == 'estonia':
        lang = 'et'
    elif country == 'italy':
        lang = 'it'
    elif country == 'latvia':
        lang = 'lv'
    elif country == 'romania':
        lang = 'ro'
    elif country == 'slovakia':
        lang = 'sk'
    elif country == 'norway':
        lang = 'no'
    elif country == 'cyprus':
        lang = 'el'
    elif country == 'poland':
        lang = 'pl'
    elif country == 'malta':
        lang = 'mt'

    # Define a stanza pipeline for splitting the paragraphs into sentences
    stanza.download(lang, processors='tokenize')
    pipeline = stanza.Pipeline(lang=lang, processors='tokenize', tokenize_batch_size=64, logging_level='INFO',
                               use_gpu=True)

    # Speeches stores all the data from all collected speeches, text only stores the texts (required for sentence splitting)
    # Together those will be used to form the final corpus
    speeches = []
    texts = []
    fieldnames = []
    existing_corp_fieldnames = []

    # Check whether there is existing data from previous corpra
    # Those files are stored on the top level in the national folder in most cases
    if country == 'ep':
        # We have a single file in case of EP parliament
        existing_corpus_files_p = [root_p.joinpath(f"ep_speeches_2009_2019_{language}.csv")]
    else:
        existing_corpus_files_p = root_p.glob('*.csv')
    if not existing_corpus_files_p:
        print(f"Could not find existing corpus for {country}. Assume that the crawled data is complete.")
    else:
        # This should be a single iteration
        for z, existing_corpus_file_p in enumerate(existing_corpus_files_p):
            with codecs.open(existing_corpus_file_p, "r", encoding="utf-8") as file:
                print(f"Start collecting {country} from existing corpus")
                reader = csv.DictReader(file)
                if z == 0:
                    # Identify the fieldnames for in the first iteration
                    existing_corp_fieldnames = reader.fieldnames
                for row in reader:
                    # Parse the date column of each row
                    date = datetime.datetime.strptime(row["date"], '%Y-%m-%d')
                    # Do the preprocessing
                    # Split it on sentence level
                    if row.get("text") and re.search("[A-Za-zΑ-Ωα-ω\u0410-\u044F]",
                                                     row.get("text")) and date.year >= 2009:
                        speeches.append(row)
                        texts.append(stanza.Document([], text=row.get("text")))
                    # Only used for debugging
                    if num_paragraphs and len(speeches) == int(num_paragraphs / 2):
                        break

    # Iterate through the years and collect all the existing data
    if country != 'ep':
        for year in years:
            current_year_p = root_p.joinpath(str(year))

            # Make sure year folder exists
            if current_year_p.is_dir():
                print(f"Start collecting {country} {year}")
                # Get all the parsed documents for that year
                parsed_files_p = current_year_p.glob('*.csv')
                for j, parsed_file_p in enumerate(parsed_files_p):
                    with codecs.open(parsed_file_p, "r", encoding="utf-8") as file:
                        reader = csv.DictReader(file)
                        if j == 0:
                            # Identify the fieldnames for in the first iteration
                            if country == "lithuania":
                                # For lithuania we have two types of csv as we combine our data with another data set
                                fieldnames = ["date", "agenda", "speechnumber", "paragraphnumber", "speaker", "speakerrole",
                                              "party", "text", "parliament", "iso3country"]
                                fieldnames_2 = ["id", "title", "from", "to", "term", "session", "meeting", "sitting",
                                                "agenda", "subcorpus", "speakerrole", "speaker_type", "speaker_party",
                                                "speaker_party_name", "party_status", "speaker_name", "speaker_gender",
                                                "speaker_birth", "text", "date"]
                                fieldnames = set(fieldnames).union(set(fieldnames_2))
                            elif country == "poland":
                                # For poland we have two types of csv as we combine our data with another data set
                                fieldnames = ['date', 'title', 'term', 'session', 'day', 'agenda', 'speechnumber',
                                              'paragraphnumber', 'speaker', 'speaker_uri', 'party', 'text', 'parliament',
                                              'iso3country', 'system']
                                fieldnames_2 = ["id", "title", "from", "to", "house", "term", "session", "meeting",
                                                "sitting", "agenda", "subcorpus", "speakerrole", "speaker_type", "party",
                                                "speaker_party_name", "party_status", "speaker", "speaker_gender",
                                                "speaker_birth", "text", "date", "speechnumber"]
                                fieldnames = set(fieldnames).union(set(fieldnames_2))
                            elif country == 'slovenia':
                                # For poland we have two types of csv as we combine our data with another data set
                                fieldnames = ["text", "id", "date", "title", "term_slv", "term", "house", "types_slv",
                                              "types_eng", "speaker_id", "speaker", "speaker_gender", "speaker_birth",
                                              "death", "speakerrole_slv", "speakerrole", "speaker_type_slv", "speaker_type",
                                              "party", "speaker_party_name", "speaker_party_name_eng", "notes", "gaps",
                                              "names", "segs", "sents", "words", "tokens", "meeting", "speechnumber"]
                                fieldnames_2 = ["id", "title", "from", "to", "house", "term", "session", "meeting",
                                                "sitting", "agenda", "subcorpus", "speakerrole", "speaker_type", "party",
                                                "speaker_party_name", "party_status", "speaker", "speaker_gender",
                                                "speaker_birth", "text", "date", "speechnumber"]
                                fieldnames = set(fieldnames).union(set(fieldnames_2))
                            elif country == 'bulgaria':
                                fieldnames = ['date', 'title', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker',
                                              'speakerrole', 'party', 'text', 'parliament', 'iso3country']
                                fieldnames_2 = ["id", "title", "from", "to", "term", "session", "meeting", "sitting",
                                                "agenda", "subcorpus", "speakerrole", "speaker_type", "party",
                                                "speaker_party_name", "party_status", "speaker", "speaker_gender",
                                                "speaker_birth", "text", "date", "speechnumber"]
                                fieldnames = set(fieldnames).union(set(fieldnames_2))
                            elif country == "croatia":
                                fieldnames = ["legislature", "session", "agenda_no", "agenda", "data_url", "is_in_agenda",
                                              "discussion_id", "speaker", "text", "speechnumber", "date", "party",
                                              "paragraphnumber"]
                                fieldnames_2 = ["id", "title", "from", "to", "house", "term", "session", "meeting",
                                                "sitting", "agenda", "subcorpus", "speakerrole", "speaker_type", "party",
                                                "speaker_party_name", "party_status", "speaker", "speaker_gender",
                                                "speaker_birth", "text", "date", "speechnumber"]
                                fieldnames = set(fieldnames).union(set(fieldnames_2))
                            else:
                                fieldnames = reader.fieldnames
                        for row in reader:
                            # Do the preprocessing
                            # Split it on sentence level
                            if row.get("text") and re.search("[A-Za-zΑ-Ωα-ω\u0410-\u044F]", row.get("text")):
                                # Add a dummy paragraph number to the row
                                speeches.append(row)
                                texts.append(stanza.Document([], text=row.get("text")))
                            # Only used for debugging
                            if num_paragraphs and len(speeches) == int(num_paragraphs):
                                break
                    # Only used for debugging
                    if num_paragraphs and len(speeches) == int(num_paragraphs):
                        break
            # Only used for debugging
            if num_paragraphs and len(speeches) == int(num_paragraphs):
                break

    # Split all the docs
    # Time the sentence splitting
    start_time = time.time()
    stanza_docs = list()
    print("Started sentence splitting")
    for i, text in enumerate(texts):
        try:
            # Run the stanza pipeline to get a stanza document object containing the splitted para
            stanza_docs.append(pipeline(text))
        except:
            # Used for debugging only
            raise AssertionError
    # End time for sentence splitting
    end_time = time.time()
    print(f'{country} sentence splitting took {round((end_time - start_time) / 60)} minutes')

    # Build the new corpus with the sentence splitted data
    print("Started post processing")
    start_time = time.time()
    instance_id = 0
    for z, row in enumerate(speeches):
        # Iterate through the sentences of the current paragraph
        for i, sentence in enumerate(stanza_docs[z].sentences):
            text = sentence.text
            if text and re.search("[A-Za-zΑ-Ωα-ω\u0410-\u044F]", text):
                # Increase the instance id, that can be used as unique identifier
                instance_id += 1
                # Copy the row to manipulate it
                new_row = row.copy()
                # Add the result to the corpus
                new_row['instance_id'] = instance_id
                new_row['sentencenumber'] = i + 1
                new_row['text'] = text
                corpus.append(new_row)

    # Add the newly added fields to the fieldnames
    output_fieldnames = ["instance_id", "date", "agenda", "speechnumber", "paragraphnumber", "sentencenumber",
                         "speaker", "party", "text", "parliament", "iso3country"]
    # Get all the remaining fields
    remaining_fieldnames = (set(fieldnames).union(set(existing_corp_fieldnames)).difference(set(output_fieldnames)))
    for fieldname in remaining_fieldnames:
        output_fieldnames.append(fieldname)

    # Write the national corpus
    write_csv(corpus_p, corpus, output_fieldnames)

    # Get end time for post processing
    end_time = time.time()
    print(f'{country} post processing took {round(end_time - start_time, 2)} seconds')


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("country", type=str,
                        help="name of the national folder that should be parsed", metavar="country")
    parser.add_argument("--language", type=str,
                        help="Language the data is in", metavar="language")
    parser.add_argument("--num_paragraphs", type=int,
                        help="Number of paragraphs to split for debugging purposes", metavar="num_paragraphs")
    parser.add_argument("--gpu_id", type=str,
                        help="Which GPU to use", metavar="gpu_id")
    args = parser.parse_args()
    country = args.country
    language = args.language
    num_paragraphs = args.num_paragraphs
    gpu_id = args.gpu_id

    main(country=country,
         language=language,
         num_paragraphs=num_paragraphs,
         gpu_id=gpu_id)
