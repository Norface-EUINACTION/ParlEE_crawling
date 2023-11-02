import pathlib
import pandas as pd
import numpy as np
import re
import glob
from eia_crawling.spiders.utils import prepare_folder_national


def main():
    # Create paths
    data_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data')
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'croatia')

    # Prepare output structure
    prepare_folder_national(data_path, country='croatia')
    legislature_data = pd.DataFrame()

    # Iterate over the missing legislatures
    for legislature in ["6", "7", "8"]:
        # Read the meta data for the sessions
        speeches_meta_data_p = target_path.joinpath(f"saziv_{legislature}_csv", f"rasprave_saziv_{legislature}.csv")
        speeches_meta_data = pd.read_csv(speeches_meta_data_p, delimiter=';')
        speeches_meta_data.columns = [column.lower() for column in speeches_meta_data.columns]

        # Read the meta data for the speeches
        speeches_p = target_path.joinpath(f"saziv_{legislature}_csv", f"transkripti_saziv_{legislature}.csv")
        speeches_data = pd.read_csv(speeches_p, delimiter=';')
        speeches_data.columns = [column.lower() for column in speeches_data.columns]

        legislature_data = legislature_data.append(
            pd.merge(speeches_meta_data, speeches_data, left_on="id", right_on="rasprava_id"))

    # Drop unnecessary information
    legislature_data.pop("je_najava")
    legislature_data.pop("rasprava_id")
    legislature_data.columns = ["legislature", "session", "agenda_no", "agenda", "data_url", "is_in_agenda", "discussion_id", "speaker", "text", "speechnumber", "date", "party"]
    legislature_data.loc[:, "paragraphnumber"] = np.nan

    # Split into the single sessions
    for date_session_key, session_data_old in legislature_data.groupby(["date", "session"]):
        if date_session_key[0] < '2009-01-01':
            continue
        session_data_old.sort_values(by=["discussion_id", "speechnumber"], inplace=True)
        session_data_new = pd.DataFrame()
        for discussion_id, discussion_data in session_data_old.groupby("discussion_id"):
            session_data_new = session_data_new.append(discussion_data)

        # Write the data
        file_name_parsed = str(date_session_key[0]) + "_" + str(date_session_key[1]) + "_parsed.csv"
        session_parsed_path = target_path.joinpath(str(date_session_key[0][:4]), file_name_parsed)
        session_data_new.to_csv(session_parsed_path, index=False)


if __name__ == "__main__":
    main()
