import pathlib
import pandas as pd
import datetime
from argparse import ArgumentParser
from eia_crawling.spiders.utils import prepare_folder_national


def main(country: str, iso2country: str):
    # Create paths
    data_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data')
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', country)
    raw_path = target_path.joinpath(f'ParlaMint-{iso2country}.txt')

    # Prepare output structure
    prepare_folder_national(data_path, country=country)

    # Merge the meta information with the textual data to get a corpus per session
    for year_p in raw_path.iterdir():
        if country == 'poland':
            metas_p = list(year_p.glob('*sejm*.tsv'))
        elif country == 'netherland':
            metas_p = list(year_p.glob('*tweedekamer*.tsv'))
        else:
            metas_p = list(year_p.glob('*.tsv'))
        if country == 'poland':
            sessions_p = enumerate(year_p.glob('*sejm*.txt'))
        elif country == 'netherland':
            sessions_p = enumerate(year_p.glob('*tweedekamer*.txt'))
        else:
            sessions_p = enumerate(year_p.glob('*.txt'))
        for index, session_p in sessions_p:
            # Country specific resctrictions
            date = datetime.datetime.strptime(session_p.stem.split("_")[1][:10], '%Y-%m-%d')
            if country == 'czechia':
                if date <= datetime.datetime.strptime('2016-06-03', '%Y-%m-%d'):
                    continue
            elif country == 'netherland':
                if date <= datetime.datetime.strptime('2019-07-04', '%Y-%m-%d'):
                    continue
            session_data = pd.read_csv(session_p, delimiter="\t", header=None, names=["id", "text"])
            meta_data = pd.read_csv(metas_p[index], delimiter="\t")
            meta_data.columns = [column.lower() for column in meta_data.columns]
            session_data = pd.merge(left=meta_data, right=session_data, on="id")

            # Set the right column names
            session_data.rename({"speaker_party": "party", "speaker_name": "speaker", "speaker_role": "speakerrole"},
                                axis=1, inplace=True)
            session_data["date"] = session_data.loc[:, "from"]
            session_data.loc[:, "speechnumber"] = session_data.index + 1

            # Write the data
            file_name_parsed = session_p.stem + "_parsed.csv"
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
