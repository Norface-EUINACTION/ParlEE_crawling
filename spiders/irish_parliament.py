import pathlib
import scrapy
import datetime
import requests
from scrapy.http.request import Request
import unidecode
import numpy as np

from .utils import (
    parse_url,
    write_txt,
    prepare_folder_national,
    write_meta,
    normalize_name,
    write_source_doc,
    write_csv
)

ROOT = pathlib.Path(__file__).absolute().parent
DATA = ROOT.joinpath("data")

# Define string constants
COUNTRY = 'ireland'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'

class IrishParliamentSpider(scrapy.Spider):
    name = "ireland"
    start_urls = []

    def __init__(self, **kwargs) -> None:
        # Do the api call to the open data api of ireland
        self.urls = []
        for year in np.arange(2009, 2021):
            resp = requests.get(f'https://api.oireachtas.ie/v1/debates?chamber_type=house&chamber=dail&date_start={year}-01-01&date_end={year}-12-31&limit=4000')
            if resp.status_code != 200:
                raise AssertionError
            # Get the results and retrieve the URLs for the XML documents
            results = resp.json().get("results")
            for result in results:
                date = result["debateRecord"]["date"]
                chamber = result["debateRecord"]["chamber"]["showAs"]
                url = result["debateRecord"]["formats"]["xml"]["uri"]
                self.urls.append({'url': url, 'date': date, 'chamber': chamber})
        prepare_folder_national(DATA, COUNTRY)
        super().__init__(**kwargs)

    def start_requests(self) -> Request:
        for data in self.urls:
            url = data['url']
            yield Request(url, callback=self.parse, meta=data)

    def parse(self, response, **kwargs):
        # get meta data
        url = response.url
        filing_date = datetime.date.today().isoformat()

        # Get the date and the year
        date = response.meta["date"]
        date_str = date.replace('-', '')
        year = date.split("-")[0]

        # Get the chamber the debate was held in and postprocess it
        chamber_str = response.meta["chamber"]
        chamber_str = chamber_str.replace(',', '')
        chamber_str = chamber_str.replace('\'', '')
        chamber_str = chamber_str.split('(')[0]
        chamber_str = unidecode.unidecode(chamber_str)
        chamber_str = "_".join(chamber_str.split())

        # Build the report name from the date and the chamber
        report_name = "_".join([date_str, chamber_str])
        report_name = str.lower(report_name)[:80]

        # Download the source page
        path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f'{report_name}.xml')
        write_source_doc(path, response.body)

        # Parse the report
        # Write meta data
        meta_data = {
            report_name: {FULL_TITLE: report_name, FILING_DATE: filing_date, URL: url}
        }
        path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f"{report_name}.json")
        write_meta(path, meta_data)