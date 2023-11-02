import pathlib
import scrapy
import datetime
import requests
from scrapy.http.request import Request
from lxml import etree
import re

from .utils import (
    prepare_folder_national,
    write_meta,
    write_source_doc,
)

ROOT = pathlib.Path(__file__).absolute().parent
DATA = ROOT.joinpath("data")

# Define string constants
COUNTRY = 'finland'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'


class FinnishParliamentSpider(scrapy.Spider):
    name = COUNTRY
    start_urls = []

    def __init__(self, **kwargs) -> None:
        # Do the api call to the open data api of ireland
        self.urls = []
        year_upper_lims_dict = {2019: 87, 2018: 181, 2017: 147, 2016: 139, 2015: 85}
        for year, upper_lim in year_upper_lims_dict.items():
            for number in range(1, upper_lim + 1):
                self.urls.append(f'https://www.eduskunta.fi/FI/vaski/Poytakirja/Documents/PTK_{number}+{year}.pdf')
        prepare_folder_national(DATA, COUNTRY)
        super().__init__(**kwargs)

    def start_requests(self) -> Request:
        for url in self.urls:
            yield Request(url, callback=self.parse)

    def parse(self, response, **kwargs):
        url = response.url
        stem = url.split("/")[-1].split(".")[0]
        year = stem.split("+")[-1]
        number = stem.split("_")[-1].split("+")[0]

        # Download the source page
        path = DATA.joinpath(NATIONAL, COUNTRY, str(year), SOURCE, f'{number}.pdf')
        write_source_doc(path, response.body)
