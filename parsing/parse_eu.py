import pathlib
import argparse
from eia_crawling.spiders.utils import write_csv
from parsing_eu_final_act_full import parse_eu_final_act_full

SPIDERS = 'spiders'
DATA = 'data'
ORIGIN = 'eu'

# Get the path to raw data
ROOT_PATH = pathlib.Path(__file__).absolute().parent.parent.joinpath(SPIDERS, DATA, ORIGIN)
print(ROOT_PATH)

def main(doc_name: str, preserve_structure: bool):
    """

    :param doc_name:            name of the doc to be parsed (WITHOUT suffix, eg. 'summary')
    :param preserve_structure:  if True, docs are saved as separate .csv files and located in year/cod folders,
                                if False, all docs are written in one .csv
    """
    # Create folder for parsed_data
    ROOT_PATH.parent.parent.joinpath('parsed_data', doc_name).mkdir(parents=True, exist_ok=True)
    parsed_path = ROOT_PATH.parent.parent.joinpath('parsed_data', doc_name)
    print(parsed_path)
    print(f'Parsing {doc_name} started.')

    corpus = []
    for year in ROOT_PATH.iterdir():
        print(f' {year.stem} is being parsed...')
        for cod in year.iterdir():
            # Parse full_final_act_1 .docs
            if doc_name == 'full_final_act_1':
                path = cod.joinpath('full', 'source')
                # Make sure the file exists
                try:
                    output = parse_eu_final_act_full(path, doc_name)
                    if preserve_structure:
                        # Write to .csv in the respective directory
                        parsed_path.joinpath(year.stem, cod.stem).mkdir(parents=True, exist_ok=True)
                        fieldnames = ['celex', 'year', 'title', 'art_no', 'text']
                        write_csv(parsed_path.joinpath(year.stem, cod.stem).joinpath(doc_name + '_parsed' + '.csv'),
                                  output, fieldnames)
                    else:
                        corpus += output
                except FileNotFoundError:
                    print(f'For {year.stem} / {cod.stem} file not found.')

    # Save as one .csv for entire corpus is preserved_structure=False
    if not preserve_structure:
        fieldnames = ['celex', 'year', 'title', 'art_no', 'text']
        write_csv(parsed_path.joinpath(doc_name + '_parsed' + '.csv'), corpus, fieldnames)

    print(f'Parsing finished successfully. Data has been saved into .csv file.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--doc_name', type=str, help='Name of the document to be parsed without suffix')
    parser.add_argument('--preserve_structure', type=bool,
                        help='Set to True if parsed documents need to be written to .csv files separately. Set to '
                             'False, if .csv must comprise of all docs.')
    args = parser.parse_args()
    main(args.doc_name, args.preserve_structure)