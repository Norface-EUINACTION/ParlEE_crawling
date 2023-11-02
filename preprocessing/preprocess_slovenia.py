import pathlib
import pandas as pd
import numpy as np
import re
from eia_crawling.spiders.utils import prepare_folder_national


def main():
    # Create paths
    data_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data')
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'slovenia')
    raw_path = target_path.joinpath(f'siParl-2.0.text')

    # Prepare output structure
    prepare_folder_national(data_path, country='slovenia')

    # Iterate over the missing legislatures
    for legislature in ["SDZ5",  "SDZ6"]:
        # Read the meta data for the sessions
        sessions_metas_p = raw_path.joinpath(f"{legislature}-sessions.tsv")
        sessions_meta_data = pd.read_csv(sessions_metas_p, delimiter="\t")
        sessions_meta_data.columns = [column.lower() for column in sessions_meta_data.columns]

        # Read the meta data for the speeches
        speeches_meta_p = raw_path.joinpath(f"{legislature}-speeches.tsv")
        speeches_meta_data = pd.read_csv(speeches_meta_p, delimiter="\t")
        speeches_meta_data.columns = [column.lower() for column in speeches_meta_data.columns]

        legislature_p = raw_path.joinpath(legislature)
        sessions_p = enumerate(legislature_p.glob('*.txt'))
        for index, session_p in sessions_p:
            year = int(re.search(r'\d{4}', session_p.stem).group())
            if year < 2009:
                continue
            # Country specific resctrictions
            session_data = pd.read_csv(session_p, header=None, names=["text"], sep='\n', skip_blank_lines=False, squeeze=True)
            # Replace nan rows with -1 for easier splitting
            session_data.loc[session_data.isna()] = -1
            # Split the session data on the -1 rows and concatenate all other rows
            speeches = np.split(session_data.values, np.where(session_data.to_numpy() == -1)[0])
            speeches = [sp[sp != -1] for sp in speeches]
            speeches = [sp for sp in speeches if not sp.size == 0]
            speeches = [" ".join(sp) for sp in speeches]
            session_data = pd.DataFrame(speeches, columns=["text"])

            # Construct session id
            session_data["session_id"] = session_p.stem.replace("-ana", "")
            # Construct speech ids
            session_data["speech_id"] = session_data["session_id"] + ".u" + list(map(str, session_data.index + 1))

            session_data = pd.merge(session_data, sessions_meta_data, left_on="session_id", right_on="id")
            session_data = pd.merge(session_data, speeches_meta_data, left_on="speech_id", right_on="speech-id")

            session_data.pop("speech-id")
            session_data.pop("session_id")
            session_data.pop("id")

            session_data.columns = [col.replace("-", "_") for col in session_data.columns]

            # Replace organisation
            session_data.loc[:, "organisations"] = "Lower house"
            session_data.loc[:, "birth"] = session_data.loc[:, "birth"].str.slice(stop=4)
            session_data.loc[:, "meeting"] = index + 1

            # Set the right column names
            session_data.rename({"speech_id": "id", "titles": "title", "mandate_eng": "term", "mandate_slv": "term_slv", "organisations": "house", "party_init": "party", "speaker_name": "speaker", "role_eng": "speaker_type", "role_slv": "speaker_type_slv", "type_eng": "speakerrole", "type_slv": "speakerrole_slv", "party_slv": "speaker_party_name", "party_eng": "speaker_party_name_eng", "sex": "speaker_gender", "birth": "speaker_birth"},  axis=1, inplace=True)
            session_data.loc[:, "speechnumber"] = session_data.index + 1

            # Write the data
            file_name_parsed = session_p.stem + "_parsed.csv"
            session_parsed_path = target_path.joinpath(str(year), file_name_parsed)
            session_data.to_csv(session_parsed_path, index=False)


if __name__ == "__main__":
    main()
