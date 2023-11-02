import pathlib
import pandas as pd
from argparse import ArgumentParser


def main(country: str):
    # Read source path
    root_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', country)
    # Create path for corpus
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders/parsed_data/national', country)
    target_path.mkdir(parents=True, exist_ok=True)

    list_of_csv = []
    for year in root_path.iterdir():
        parsed_docs = list(year.glob('*.csv'))
        list_of_csv += parsed_docs

    combined_csv = pd.concat([pd.read_csv(f) for f in list_of_csv])
    combined_csv.to_csv(target_path.joinpath(f'{country}_corpus.csv'), index=False)
    print('Corpus has been successfully written.')


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("country", type=str,
                        help="name of the national folder that should be parsed", metavar="path")
    args = parser.parse_args()
    input_path = args.country
    main(country=input_path)
