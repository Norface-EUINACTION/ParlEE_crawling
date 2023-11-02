import pathlib
import codecs
from eia_crawling.spiders.utils import prepare_folder_national, write_txt
import re
import datetime
from calendar import monthrange
from sys import platform

SOURCE = 'source'

MONTHS = {
    "Ιανουαρίου": 1,
    "Φεβρουαρίου": 2,
    "Μαρτίου": 3,
    "Απριλίου": 4,
    "Μαΐου": 5,
    "Ιουνίου": 6,
    "Ιουλίου": 7,
    "ἰουλίου": 7,
    "ουλίου": 7,
    "ἰΙουλίου": 7,
    "Αυγούστου": 8,
    "Σεπτεμβρίου": 9,
    "Οκτωβρίου": 10,
    "Νοεμβρίου": 11,
    "∆εκεμβρίου": 12,
    "Δεκεμβρίου": 12}


def main():
    # todo: Code is not operator system independent ==> \r\n on windows as line separator...
    if platform == 'linux':
        raise ValueError("Parsing for this OS not implemented")
    elif platform == 'win32':
        pass
    else:
        raise ValueError("Parsing for this OS not implemented")

    # Create paths
    data_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data')
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'cyprus')
    raw_path = target_path.joinpath('raw')

    # # Prepare output structure
    prepare_folder_national(data_path, country='cyprus')

    # Split the pdfs into single txt files

    txt_p = list(raw_path.glob('*.txt'))
    for index, session_p in enumerate(txt_p):
        # # Count the number of splitted documents per pdf for verification purposes
        i = 0
        with codecs.open(str(session_p), encoding='utf-8') as f:
            session_data = f.readlines()
            session_data = " ".join(session_data)
        session_data = session_data.replace('\r\n', '__br__')

        # Used to verify dates
        first_date = re.search(r"\(.*\)", session_p.stem).group()
        first_date = first_date.split("-")[0].strip("( ")
        first_date = datetime.datetime.strptime(first_date, '%d.%m.%Y')
        previous_date = first_date

        error_dates = 0

        sittings_list = re.split(
            r'__br__\s*(?=Πρακτικά\s+της\s+Βουλής|Πρακτικά\s+τῆης\s+Βουλής|Πρακτικά\s+της\s+Βουλι\'ἷς|Πρακτικά\s+της\s+Βουλἡξ|Πρακτικά\s+τῆς\s+Βουλής)',
            session_data)
        if sittings_list:
            for j, sitting_data in enumerate(sittings_list):
                if isinstance(sitting_data, str):
                    sitting_data = sitting_data.strip()
                if sitting_data == '__br__' or not re.search(
                        r'(?<=__br__)\s*\(*\s*Αρ\.\s*(\d{1,3}|Ἵ)\s*\)*\s*(?=__br__)|(?<=__br__)\s*.{,3}κτακτη συνεδρίαση\s*(?=__br__)|(?<=__br__)\s*\.?Ὥρα ἕναρξης.+?(?=__br__)',
                        sitting_data):
                    # Skip all splits that are rubbish
                    continue
                # Identify the date, parliamentary period, session and sitting
                # date_raw_match = re.search(r'(?<=__br__)\s*Συνεδρίαση.*?(?=__br__)|(?<=__br__)\s*.κτακτη\s+συνεδρίαση.*?(?=__br__)|(?<=__br__)\s*Ειδική\s+συνεδρίαση.*?\s*(?=__br__)', sitting_data)
                date_raw_match = re.search(r"(__br__\s*__br__|__br__).*?((__br__\s*__br__|__br__).*?__br__)",
                                           sitting_data)
                if date_raw_match:
                    date_raw = date_raw_match.group(2)
                    # Remove unnecessary stuff from the date
                    date_raw = date_raw.replace("__br__", " ")
                    date_raw = re.sub(
                        r'\s*Συνεδρίαση\s*|\s*.κτακτη\s+συνεδρίαση\s*|\s*Ειδική\s+συνεδρίαση\s*|Εἰδική\s+συνεδρίαση\s*',
                        '', date_raw)
                    date_raw = date_raw.strip()
                    date_list_raw = date_raw.split()
                    date_list = date_list_raw.copy()
                    try:
                        date_list[1] = str(MONTHS[date_list_raw[1]])
                        date_list[2] = re.search(r'\d{4}', date_list_raw[2]).group()
                        # Manual replace the month by a number and clean the day and the year
                        date_list_raw[0] = re.sub(r'[α-ωίϊΐόάέύϋΰήώ\-\"\.]*?', '', date_list_raw[0])
                        # Catch cases in which greek equivalent of '3th' is recognized as '355'
                        if len(date_list_raw[0]) == 2 and int(date_list_raw[0]) > monthrange(int(date_list[2]), int(date_list[1]))[1]:
                            # e.g. 30
                            date_list[0] = re.search(r'\d', date_list_raw[0]).group()
                        elif len(date_list_raw[0]) == 3:
                            # e.g. 205
                            date_list[0] = re.search(r'\d', date_list_raw[0]).group()
                        elif len(date_list_raw[0]) == 4:
                            # e.g. 1675
                            date_list[0] = re.search(r'\d\d', date_list_raw[0]).group()
                        elif len(date_list_raw[0]) == 5:
                            # e.g. E1675
                            date_list[0] = re.search(r'\d\d', date_list_raw[0]).group()
                        else:
                            date_list[0] = date_list_raw[0]
                    except:
                        raise AssertionError
                    date = " ".join(date_list)
                    try:
                        date = datetime.datetime.strptime(date, '%d %m %Y')
                    except ValueError:
                        raise AssertionError
                    if date < previous_date:
                        # Increase chances that we get the right date ==> Dates have to be ascending
                        # Happens when we discard to much of the date
                        date_list[0] = re.search(r'\d{1,2}', date_list_raw[0]).group()
                        date = " ".join(date_list)
                        try:
                            # In case the date is invalid, we kept to much
                            date = datetime.datetime.strptime(date, '%d %m %Y')
                        except ValueError:
                            date_list[0] = re.search(r'\d', date_list_raw[0]).group()
                            date = " ".join(date_list)
                            date = datetime.datetime.strptime(date, '%d %m %Y')
                        if date < previous_date:
                            error_dates += 1
                    previous_date = date

                else:
                    raise AssertionError

                if date.year <= 2008:
                    continue
                # Get the parliamentary period and the session
                period_session_match = re.search(r'(?<=__br__).*?(--|-|–).*?(?=__br__)', sitting_data)
                if period_session_match:
                    period_session_raw = period_session_match.group()
                    if "--" in period_session_raw:
                        period_session_list = period_session_raw.split("--")
                    elif "-" in period_session_raw:
                        period_session_list = period_session_raw.split("-")
                    elif "–" in period_session_raw:
                        period_session_list = period_session_raw.split("–")
                    else:
                        raise AssertionError
                    period_raw = period_session_list[0]
                    session_raw = period_session_list[1]
                    period = period_raw.strip('_br ', )
                    session = session_raw.strip('_br ', )
                else:
                    raise AssertionError
                # Get the sitting
                sitting_match = re.search(
                    r'(?<=__br__)\s*\(*\s*Αρ\.\s*(\d{1,3}|Ἵ)\s*\)*\s*(?=__br__)|(?<=__br__)\s*.{,3}κτακτη συνεδρίαση\s*(?=__br__)',
                    sitting_data)
                if sitting_match:
                    sitting_raw = sitting_match.group()
                    sitting = sitting_raw.strip('Αρ.() ')
                else:
                    # In some cases the sitting is not numbered
                    sitting = '0'

                sitting_data = sitting_data.replace('__br__', '\r\n')

                i += 1
                # Write the data
                file_name = date.isoformat()[:10] + "_" + period + "_" + session + "_" + sitting + ".txt"
                sitting_source_path = target_path.joinpath(f'{date.year}', SOURCE, file_name)
                write_txt(sitting_source_path, sitting_data)
        else:
            raise AssertionError
        # Print the number of documents per pdf
        print(f"Number of sittings: {i}")
        print(f"Number of error dates {error_dates}")

        f.close()
        if i != len(sittings_list) - 2:
            # Double check the parsing in this case
            print("Double check")


if __name__ == "__main__":
    main()
