import pathlib
import pandas as pd
import numpy as np
import re
import glob
from eia_crawling.spiders.utils import prepare_folder_eu


def main():
    # Create paths
    data_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'eu', 'mep_speeches',
                                                                         'release', 'en')
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'eu', 'mep_speeches')

    file_name = "mep_speeches_2009_2019.csv"

    # Get train, dev and test data
    meta_columns = ["term", "date", "id", "type", "speaker_role", "speaker_id", "agenda"]
    speech_columns = ["text"]
    speaker_columns_all = ["type", "speaker_id", "speaker", "gender", "url"]
    speaker_columns = ["speaker_id", "speaker", "gender", "url"]

    meta_data_train = pd.read_csv(
        data_path.joinpath('train', 'text', 'internal', 'raw', 'ep-asr.lm.tr-am-train.20080901-20200527.en.csv'),
        delimiter=';', header=None, names=meta_columns)
    speeches_train = pd.read_csv(
        data_path.joinpath('train', 'text', 'internal', 'raw', 'ep-asr.lm.tr-am-train.20080901-20200527.en.txt'),
        header=None, delimiter='\t', names=speech_columns)
    speakers_train = pd.read_csv(
        data_path.joinpath('train', 'original_audio', 'metadata', 'speakers.csv'),
        header=None, delimiter=';', names=speaker_columns_all, usecols=speaker_columns)

    meta_data_dev = pd.read_csv(
        data_path.joinpath('dev', 'text', 'raw', 'ep-asr.lm.dev.spk-dep.tr.en.csv'),
        delimiter=';', header=None, names=meta_columns)
    speeches_dev = pd.read_csv(
        data_path.joinpath('dev', 'text', 'raw', 'ep-asr.lm.dev.spk-dep.tr.en.orig.txt'),
        header=None, delimiter='\t', names=speech_columns)
    speakers_dev = pd.read_csv(
        data_path.joinpath('dev', 'original_audio', 'spk-dep', 'metadata', 'speakers.csv'),
        header=None, delimiter=';', names=speaker_columns_all, usecols=speaker_columns)

    meta_data_test = pd.read_csv(
        data_path.joinpath('test', 'text', 'raw', 'ep-asr.lm.test.spk-dep.tr.en.csv'),
        delimiter=';', header=None, names=meta_columns)
    speeches_test = pd.read_csv(
        data_path.joinpath('test', 'text', 'raw', 'ep-asr.lm.test.spk-dep.tr.en.orig.txt'),
        header=None, delimiter='\t', names=speech_columns)
    speakers_test = pd.read_csv(
        data_path.joinpath('test', 'original_audio', 'spk-dep', 'metadata', 'speakers.csv'),
        header=None, delimiter=';', names=speaker_columns_all, usecols=speaker_columns)

    # Join the data
    data_train = pd.concat([meta_data_train, speeches_train], axis=1)
    data_train = data_train.merge(speakers_train, left_on="speaker_id", right_on="speaker_id")

    data_dev = pd.concat([meta_data_dev, speeches_dev], axis=1)
    data_dev = data_dev.merge(speakers_dev, left_on="speaker_id", right_on="speaker_id")

    data_test = pd.concat([meta_data_test, speeches_test], axis=1)
    data_test = data_test.merge(speakers_test, left_on="speaker_id", right_on="speaker_id")

    data = pd.concat([data_train, data_dev, data_test], axis=0, ignore_index=True)

    # Filter and sort the data
    data = data.loc[(data.date >= '2009-01-01') & (data.date < '2020-01-01') & (data.speaker_role == 'mep'), :]
    data.sort_values(by=["date", "id"], inplace=True)
    data["party"] = None
    data.reset_index(drop=True, inplace=True)

    # Merge party data in
    meta_data_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'eu', 'mep_speeches',
                                                                              'meta_data')

    party_data_2014 = pd.read_excel(meta_data_path.joinpath('EP-PE_LMEPS(1979)0001_XL.xls'))
    party_data_2014.fillna(method='ffill', inplace=True)
    party_data_2014[["last_name", "first_name"]] = party_data_2014.NOM.str.split(r'(?<=[A-Z])\s(?=[A-Z][a-zà-ÿ])',
                                                                                 expand=True)
    party_data_2014.loc[:, "speaker"] = party_data_2014.loc[:, "first_name"] + " " + party_data_2014.loc[:, "last_name"]
    party_data_2014.loc[:, "speaker"] = party_data_2014.speaker.str.upper()

    party_data_2019 = pd.read_excel(meta_data_path.joinpath('EP-PE_LMEPS(2018)0002_XL.xlsx'))
    party_data_2019.fillna(method='ffill', inplace=True)
    party_data_2019.loc[:, "speaker"] = party_data_2019.loc[:, "First name"] + " " + party_data_2019.loc[:,
                                                                                     "Family name"]
    party_data_2019.loc[:, "speaker"] = party_data_2019.speaker.str.upper()

    party_data_current = pd.read_xml(meta_data_path.joinpath('MEPs_2019.xml'))
    party_data_outgoing = pd.read_xml(meta_data_path.joinpath('MEPs_2019_outgoing.xml'))

    def get_party_2014(value, party_data):
        # Get the speaker uri of the current group
        speaker = value.iloc[0].speaker
        # First and last name are filled, try to get the party
        if speaker:
            # Use the date to find the correct party assignment
            date = value.iloc[0].date
            result = party_data.loc[
                (party_data.speaker == speaker) & (party_data.start_date <= date) & (party_data.end_date >= date)]
            # If the speaker was member in a party at the time of the speech add the party to the dataset
            if not result.empty:
                value.loc[:, "party"] = result.iloc[0].loc["Groupe politique*"]
        return value

    def get_party_2019(value, party_data):
        # Get the speaker uri of the current group
        speaker = value.iloc[0].speaker
        # First and last name are filled, try to get the party
        if speaker:
            # Use the date to find the correct party assignment
            result = party_data.loc[
                (party_data.speaker == speaker)]
            # If the speaker was member in a party at the time of the speech add the party to the dataset
            if not result.empty:
                value.loc[:, "party"] = result.iloc[0].loc["Political group"]
        return value

    def get_party_current(value, party_data):
        # Get the speaker uri of the current group
        speaker_id = value.iloc[0].speaker_id
        # First and last name are filled, try to get the party
        if speaker_id:
            # Use the date to find the correct party assignment
            result = party_data.loc[(party_data.id == int(speaker_id))]
            # If the speaker was member in a party at the time of the speech add the party to the dataset
            if not result.empty:
                value.loc[:, "party"] = result.iloc[0].loc["politicalGroup"]
        return value

    # Iterate over speaker and date groups to find the correct party
    data.loc[data.term < 8] = data.loc[data.term < 8].groupby(["speaker", "date"], dropna=False).apply(get_party_2014,
                                                                                                       party_data_2014)
    data.loc[data.term == 8] = data.loc[data.term == 8].groupby(["speaker", "date"], dropna=False).apply(get_party_2019,
                                                                                                         party_data_2019)
    data.loc[data.term > 8] = data.loc[data.term > 8].groupby(["speaker", "date"], dropna=False).apply(
        get_party_current,
        party_data_current)
    data.loc[data.term > 8] = data.loc[data.term > 8].groupby(["speaker", "date"], dropna=False).apply(
        get_party_current,
        party_data_outgoing)

    # Replace full party names
    data.loc[data.party == "Group of the European People's Party (Christian Democrats)", "inst"] = "EPP"
    data.loc[data.party == "Identity and Democracy Group", "inst"] = "ID"
    data.loc[data.party == "Group of the Progressive Alliance of Socialists and Democrats in the European Parliament", "inst"] = "S&D"
    data.loc[data.party == "European Conservatives and Reformists Group", "inst"] = "ECR"
    data.loc[data.party == "Renew Europe Group", "inst"] = "Renew"
    data.loc[data.party == "Group of the Greens/European Free Alliance", "inst"] = "Greens/EFA"
    data.loc[data.party == "The Left group in the European Parliament - GUE/NGL", "inst"] = "GUE/NGL"
    data.loc[data.party == "Group of the European United Left - Nordic Green Left", "inst"] = "GUE/NGL"
    data.loc[data.party == "Non-attached Members", "party"] = "NI"

    data.to_csv(target_path.joinpath(file_name), index=False)


if __name__ == "__main__":
    main()
