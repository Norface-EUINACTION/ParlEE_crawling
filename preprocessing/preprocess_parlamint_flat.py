import pathlib
import pandas as pd
from argparse import ArgumentParser
from eia_crawling.spiders.utils import prepare_folder_national
import re
# Preprocess parlamint data that has a flat structure in the .txt folder (no subfolders for the years)


def main(country, iso2country):
    # Create paths
    data_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data')
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', country)
    raw_path = target_path.joinpath(f'ParlaMint-{iso2country}.txt')

    # Prepare output structure
    prepare_folder_national(data_path, country=country)

    # Merge the meta information with the textual data to get a corpus per session
    metas_p = list(raw_path.glob('*.tsv'))
    for index, session_p in enumerate(raw_path.glob('*.txt')):
        if "README" in str(session_p):
            continue

        meta_data = pd.read_csv(metas_p[index-1], delimiter="\t")
        meta_data.columns = [column.lower() for column in meta_data.columns]

        if country == "latvia":
            year = re.search(r'\d{4}', session_p.stem).group()
        elif country == "croatia":
            year = meta_data.loc[0, "from"][:4]
        else:
            year = session_p.stem.split("_")[1][:4]
        if country == "spain" and int(year) < 2019:
            continue
        session_data = pd.read_csv(session_p, delimiter="\t", header=None, names=["id", "text"])
        session_data = pd.merge(left=meta_data, right=session_data, on="id")

        # Set the right column names
        session_data.rename({"speaker_party": "party", "speaker_name": "speaker", "speaker_role": "speakerrole"}, axis=1, inplace=True)
        session_data["date"] = session_data.loc[:, "from"]
        session_data.loc[:, "speechnumber"] = session_data.index + 1

        # Write the data
        file_name_parsed = session_p.stem + "_parsed.csv"
        year_p = target_path.joinpath(year)
        session_parsed_path = target_path.joinpath(year_p.name, file_name_parsed)
        session_data.to_csv(session_parsed_path, index=False)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("country", type=str,
                        help="Country name (lowercase)", metavar="path")
    parser.add_argument("iso2country", help="iso2country code of the respective country (capitalized)", type=str)
    args = parser.parse_args()
    country = args.country
    iso2country = args.iso2country

    main(country=country,
         iso2country=iso2country)
