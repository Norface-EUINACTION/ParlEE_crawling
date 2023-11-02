import pathlib
import pandas as pd
import numpy as np
from argparse import ArgumentParser
from eia_crawling.spiders.utils import prepare_folder_national


def main():
    # Create paths
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'greece', 'Greek_Parliament_Proceedings_1989_2019.csv')
    data = pd.read_csv(target_path)

    data = data.loc[data.sitting_date >= '2009-01-01']

    # Rename columns
    data.rename({"member_name": "speaker", "sitting_date": "date", "political_party": "party", "speaker_info": "speakerrole", "speech": "text", "parliamentary_period": "period", "parliamentary_session": "session", "parliamentary_sitting": "sitting"}, axis=1, inplace=True)

    # Introduce speechnumber
    data.loc[:, "speechnumber"] = data.index + 1
    # Introduce paragraphnumber
    data.loc[:, "paragraphnumber"] = np.nan
    data.loc[:, "agenda"] = np.nan
    data.loc[:, "parliament"] = "GR-Vouli ton Ellinon"
    data.loc[:, "iso3country"] = "GRC"

    data.to_csv(target_path, index=False)


if __name__ == "__main__":
    main()
