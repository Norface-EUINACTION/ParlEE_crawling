import pathlib
import numpy as np
import pandas as pd
import datetime
from langdetect import detect
from langdetect import DetectorFactory

DetectorFactory.seed = 0


def main():
    def get_language(text):
        lang = detect(text)
        return lang

    # Helper function to read party
    def get_party(value, party_data):
        # Get the speaker uri of the current group
        mep_id = int(value.iloc[0].mep_id)
        # First and last name are filled, try to get the party
        if mep_id:
            # Use the date to find the correct party assignment
            date = value.iloc[0].date
            result = party_data.loc[
                (party_data.id == mep_id) & (party_data.joined <= date) & (party_data.left >= date)]
            # If the speaker was member in a party at the time of the speech add the party to the dataset
            if not result.empty:
                value.loc[:, "party"] = result.iloc[0].inst
            # else:
            #     raise AssertionError
        return value

    def get_name(value, party_data):
        """
        Get the politicians name by mep id
        """
        mep_id = int(value.iloc[0].mep_id)
        if mep_id:
            result = party_data.loc[(party_data.id == mep_id)]
            if not result.empty:
                value.loc[:, "speaker"] = result.iloc[0].get("name").title()
            # else:
            #     value.loc[:, "speaker"] = ""
        return value

    root_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'ep')
    years = list(np.arange(2009, 2022))

    data = pd.DataFrame()

    # Concate all the sessions
    for year in years:
        year_path = root_path.joinpath(str(year))
        filepaths = year_path.glob('*.csv')
        for filepath in filepaths:
            data_tmp = pd.read_csv(filepath)
            data = data.append(data_tmp)

    # Get language
    data.reset_index(drop=False, inplace=True)
    # data = data.iloc[-1000:]
    data.loc[:, "language"] = data.text.apply(get_language)

    # Prepare merging of party data
    meta_data_path = root_path.joinpath('meta_data')
    party_data = pd.read_csv(meta_data_path.joinpath('MEPsBio.csv'), infer_datetime_format=True,
                             parse_dates=["joined"], dayfirst=True)
    party_data = party_data.loc[party_data.type == "Parliament Group"]
    # Set end date of our time period
    party_data.loc[party_data.left == "...", 'left'] = '31/12/2019'
    party_data.loc[:, "left"] = pd.to_datetime(party_data.loc[:, "left"], dayfirst=True)

    # Append 2019 data
    party_data_current = pd.read_xml(meta_data_path.joinpath('MEPs_2019.xml'))
    party_data_current.loc[:, "mandate-start"] = '02/07/2019'
    party_data_current.loc[:, "mandate-end"] = '31/12/2019'
    party_data_outgoing = pd.read_xml(meta_data_path.joinpath('MEPs_2019_outgoing.xml'))
    party_data_current = party_data_current.append(party_data_outgoing)
    party_data_current.drop(columns=["nationalPoliticalGroup", "leg"], inplace=True)
    party_data_current.rename(columns={'fullName': 'name', 'mandate-start': 'joined', 'mandate-end': 'left', 'politicalGroup': 'inst'}, inplace=True)
    party_data_current.loc[:, "joined"] = pd.to_datetime(party_data_current.loc[:, "joined"], dayfirst=True)
    party_data_current.loc[:, "left"] = pd.to_datetime(party_data_current.loc[:, "left"], dayfirst=True)

    party_data = party_data.append(party_data_current)
    del party_data_current, party_data_outgoing

    party_data.sort_values(by="joined", inplace=True, ascending=False)
    party_data.reset_index(drop=True, inplace=True)

    party_data.loc[party_data.inst == "Group of the European People's Party (Christian Democrats)", "inst"] = "EPP"
    party_data.loc[party_data.inst == "Group of the Alliance of Liberals and Democrats for Europe", 'inst'] = "ALDE"
    party_data.loc[party_data.inst == "Group of the Progressive Alliance of Socialists and Democrats in the European Parliament", "inst"] = "S&D"
    party_data.loc[party_data.inst == "European Conservatives and Reformists Group", "inst"] = "ECR"
    party_data.loc[party_data.inst == "Group of the Greens/European Free Alliance", "inst"] = "Greens/EFA"
    party_data.loc[party_data.inst == "Group of the European United Left - Nordic Green Left", "inst"] = "GUE/NGL"
    party_data.loc[party_data.inst == "Non-attached Members", "inst"] = "NI"
    party_data.loc[party_data.inst == "Europe of Freedom and Direct Democracy Group", 'inst'] = "EFDD"
    party_data.loc[party_data.inst == "Europe of freedom and democracy Group", 'inst'] = "EFD"
    party_data.loc[party_data.inst == "Europe of Nations and Freedom Group", 'inst'] = "ENF"
    party_data.loc[party_data.inst == "Group of the European People's Party (Christian Democrats) and European Democrats", 'inst'] = "EPP"
    party_data.loc[party_data.inst == "Socialist Group in the European Parliament", 'inst'] = "S&D"
    party_data.loc[party_data.inst == "Renew Europe Group", 'inst'] = "Renew"
    party_data.loc[party_data.inst == "Identity and Democracy Group", 'inst'] = "ID"
    party_data.loc[party_data.inst == "Union for Europe of the Nations Group", 'inst'] = "UEN"
    party_data.loc[party_data.inst == "The Left group in the European Parliament - GUE/NGL", 'inst'] = "GUE/NGL"
    party_data.loc[party_data.inst == "Independence/Democracy Group", 'inst'] = "IND/DEM"
    party_data.loc[party_data.inst == "Group of the European United Left - Nordic Green Left", 'inst'] = "GUE/NGL"
    party_data.loc[party_data.inst == "Confederal Group of the European United Left - Nordic Green Left", 'inst'] = "GUE/NGL"

    # Split the data per language and merge with the talk of europe data
    for index, data_tmp in data.groupby("language"):
        data_lang = pd.DataFrame()
        file_name = f'ep_speeches_2009_2019_{index}.csv'
        file_name_talk = f"talk_of_europe_2009_2017_{index}.csv"
        file_path_talk = root_path.joinpath('talk_of_europe', file_name_talk)
        if file_path_talk.is_file():
            data_talk = pd.read_csv(file_path_talk)
            data_lang = data_lang.append(data_talk)
        data_lang = data_lang.append(data_tmp)
        data_lang.reset_index(drop=True, inplace=True)

        # Merging missing mep meta data
        # Iterate over speaker and date groups to find the correct party
        data_lang.loc[data_lang.party.isna(), :] = data_lang.loc[data_lang.party.isna(), :].groupby(["mep_id", "date"], dropna=False).apply(get_party, party_data)

        # Try getting the name of the meps
        data_lang.loc[(data_lang.speaker.isna()) | (~data_lang.speaker.str.contains(" ", na=False)) | (data_lang.speaker.str.contains("^(La|Le|El|Il|Der|Die)\s", regex=True, na=False)) | (data_lang.language == 'bg') | (data_lang.language == 'el'), :] = data_lang.loc[(data_lang.speaker.isna()) | (~data_lang.speaker.str.contains(" ", na=False)) | (data_lang.speaker.str.contains("^(La|Le|El|Il|Der|Die)\s", regex=True, na=False)) | (data_lang.language == 'bg') | (data_lang.language == 'el'), :].groupby(["mep_id", "date"],dropna=False).apply(get_name, party_data)

        data_lang.to_csv(root_path.joinpath(file_name), index=False)


if __name__ == "__main__":
    main()
