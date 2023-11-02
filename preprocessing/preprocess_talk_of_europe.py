import pathlib
import pandas as pd


def main():
    # Create paths
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'ep', 'talk_of_europe')

    data = pd.read_csv(target_path.joinpath("talk_of_europe_2009_2017_raw.csv"))
    written_flag = pd.read_csv(target_path.joinpath("talk_of_europe_2009_2017_written_flag.csv"))

    data = data.merge(written_flag, how='left', on='speechnumber')

    # If translation is available use it
    translated_index = data.loc[(data.language != 'en') & (pd.notna(data.translated_text)), "original_text"].index
    data.loc[translated_index, "original_text"] = data.loc[translated_index, "translated_text"]
    data.loc[translated_index, "language"] = 'en'
    data.rename(columns={"original_text": "text"}, inplace=True)
    data.pop("translated_text")

    # Add speechnumber and agendanumber
    data.rename(columns={"agendanumber": "agenda_id", "speechnumber": "speech_id"}, inplace=True)
    data.loc[:, "agendanumber"] = data.agenda_id.str.extract(pat=r'((?<=\.)\d*$)').astype(int)
    data.loc[:, "speechnumber"] = data.speech_id.str.extract(pat=r'((?<=\.)\d\d?-.*?$)')

    data.sort_values(by=["date", "agendanumber", "speechnumber"], inplace=True)
    for index, data_tmp in data.groupby("language"):
        file_name = f"talk_of_europe_2009_2017_{index}.csv"
        data_tmp.to_csv(target_path.joinpath(file_name), index=False)


if __name__ == "__main__":
    main()
