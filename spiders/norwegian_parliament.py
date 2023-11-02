import pathlib
import scrapy
import datetime
import requests
import locale
import time
from bs4 import BeautifulSoup
from .utils import (
    prepare_folder_national,
    write_meta,
    write_source_doc,
)

ROOT = pathlib.Path(__file__).absolute().parent
DATA = ROOT.joinpath("data")

# Define string constants
COUNTRY = 'norwegian'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'
YEARS = ["2016", "2017", "2018", "2019", "2020", "2021"]


class NorwegianParliamentSpider(scrapy.Spider):
    name = COUNTRY
    base_urls = []
    all_urls = []
    def __init__(self, years=None, **kwargs) -> None:

        if years is None:
            years = YEARS

        self.base_url = "https://www.stortinget.no"
        #self.session_default_id = 0
        self.session_id = 0
        # First Year
        #corr_url = self.base_url + "/no/Saker-og-publikasjoner/Publikasjoner/Referater/?pid={}-{}#primaryfilter".format(
        #    int(YEARS[0]) - 1, YEARS[0])
        #self.base_urls.append(corr_url)

        for single_year in years:
            corr_url = self.base_url + "/no/Saker-og-publikasjoner/Publikasjoner/Referater/?pid={}-{}#primaryfilter".format(
                single_year, int(single_year) + 1)

            self.base_urls.append(corr_url)

        prepare_folder_national(DATA, COUNTRY)
        self.download_html_and_metadata()
        super().__init__(**kwargs)

    def download_html_and_metadata(self):

        # Get all URLS to the meetings
        self.construct_all_urls()

        for url in self.all_urls:

            # Open HTML
            website = requests.get(url)
            results = BeautifulSoup(website.content, 'html.parser')
            time.sleep(1)

            # Get Meta Data
            try:
                meta_data, path_html, path_json, year = self.construct_meta_data(url, results)
                if int(year) < int(YEARS[0]):
                    continue
            except:
                return

            # Create HTML and Json File
            self.download_html_json(website, path_html, path_json, meta_data)


    def construct_all_urls(self):

        for url in self.base_urls:
            website = requests.get(url)
            time.sleep(2)
            results = BeautifulSoup(website.content, 'html.parser')

            # List items are all urls to the meetings
            find_all = results.find_all('h3', class_='listitem-title')
            for element in find_all:

                # href contains the link to the meetings
                element_a = element.find_all('a', href=True)
                for single_href in element_a:
                    self.all_urls.append(single_href['href'])

        # View whole meeting in HTML
        open_meeting = "?all=true"
        for index, url in enumerate(self.all_urls):
            # Construct url with base and with opening the meeting in HTML
            self.all_urls[index] = self.base_url + url + open_meeting

    def construct_meta_data(self, url, results):

        #try:
        #    session_id = results.find('meta', attrs={'name': 'MA.Meeting-id'})["content"]
        #except:
        #    session_id = '{:05}'.format(self.session_default_id)
        #    self.session_default_id += 1
        self.session_id += 1

        date = results.find('meta', attrs={'name': 'DC.Date'})["content"].strip('\t\n\r ')

        # Set locale to Belgium in order to parse Belgian dates
        locale.setlocale(locale.LC_TIME, 'no_NO')
        date_format = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        locale.setlocale(locale.LC_TIME, 'nl_BE')
        year = str(date_format.year)
        date = date_format.strftime('%Y%m%d')
        date_month_day = date_format.strftime('%m%d')
        filing_date = datetime.date.today().isoformat()

        # Build the meta data
        date_abbreviation = year[2:] + date_month_day

        report_name = f'{date_abbreviation}_{self.session_id}_{REPORT}'
        title = f'{date}_{self.session_id}'

        meta_data = {
            report_name: {FULL_TITLE: title, FILING_DATE: filing_date, URL: url}
        }

        path_html = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f'{report_name}.html')

        path_json = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f"{report_name}.json")

        return meta_data, path_html, path_json, year


    def download_html_json(self, response, path_html, path_json, meta_data, **kwargs):
        # Start URLs lead to the overview page of a legislative period
        # Go through all documents/rows of the legislative period and download them
        # Download the source page
        write_source_doc(path_html, response.content)

        # Parse the report
        # Write meta data
        write_meta(path_json, meta_data)
