import pathlib
import scrapy
from lxml import html
from scrapy.selector import Selector
from scrapy.http import HtmlResponse
from scrapy.linkextractors import LinkExtractor
import datetime

from .utils import (
    parse_url,
    write_txt,
    prepare_folder_national,
    write_meta,
    normalize_name,
    write_source_doc,
    write_csv
)

MONTHS = {
    'janvier': '1',
    'février': '2',
    'mars': '3',
    'avril': '4',
    'mai': '5',
    'juin': '6',
    'juillet': '7',
    'août': '8',
    'septembre': '9',
    'octobre': '10',
    'novembre': '11',
    'décembre': '12'
}

ROOT = pathlib.Path(__file__).absolute().parent
DATA = ROOT.joinpath("data")

# Define string constants
COUNTRY = 'france'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'


# print(f'{ROOT=}')
# print(f'{DATA=}')
class FrenchParliamentSpider(scrapy.Spider):
    name = "france"
    start_urls = [
        'http://www.assemblee-nationale.fr/15/debats/index.asp',
        'http://www.assemblee-nationale.fr/14/debats/index.asp',
        'http://www.assemblee-nationale.fr/13/debats/index.asp'
    ]

    def __init__(self, **kwargs) -> None:
        # Helper to get the links on overview page (e.g. http://www.assemblee-nationale.fr/15/debats/index.asp)
        # and on session page (e.g. http://www.assemblee-nationale.fr/15/cri/2020-2021/)
        self.link_extractor_overview = LinkExtractor(
            restrict_xpaths='//div[ @class ="content right-shadow-alt"]//ul[@ class ="liens-liste"]//a')
        self.link_extractor_reports = LinkExtractor(
            restrict_xpaths='//h1//a')
        prepare_folder_national(DATA, COUNTRY)
        super().__init__(**kwargs)

    def parse(self, response, **kwargs):
        # Get all links to overview of the parliamentary sessions
        overview_links = self.link_extractor_overview.extract_links(response)
        # Hardcode the required links (after that is no longer relevant)
        if '13' in response.url:
            overview_links = overview_links[:13]
        # Navigate to the overview page
        yield from response.follow_all(
            overview_links,
            callback=self.parse_overview,
            **kwargs
        )

    def parse_overview(self, response, **kwargs):
        # Get all reports from the overview page
        report_links = self.link_extractor_reports.extract_links(response)
        yield from response.follow_all(
            report_links,
            callback=self.parse_report,
            **kwargs
        )

    def parse_report(self, response, **kwargs):
        # Get meta information
        # Take the last four characters of the second last element of the URL (.../20190002.asp ==> 0002)
        report_prefix = response.url.split("/")[-1].split(".")[0]
        # Special naming for a few reports (budget in 2009 and 2010) (.../C007.asp)
        if report_prefix.isnumeric():
            report_name = "_".join([report_prefix[-8:], REPORT])
        else:
            report_name = report_prefix
            # C007_session

        # Get the date (need to handle few exceptional date formulations)
        date_list = response.xpath('//h1[not(parent::div[@id="somjo"])]/text()[not(parent::sup)]').getall()
        # Check whether date is empty
        if not date_list:
            # Try to get the date from the title
            date_list = response.xpath('//title//text()').getall()
        if date_list:
            date_list = [x.strip('\n ') for x in date_list]
            date = " ".join(date_list)
            date = date.split()[-3:]
            # Replace month with number
            date[1] = MONTHS[date[1]]
            # Secure that day is only the number (first elements of the string)
            if len(date[0]) > 2:
                # Exclude st, nd, rd
                date[0] = date[0][:-2]
            year = date[2]
        else:
            # No date retrieved
            raise AssertionError

        title = response.xpath('//title/text()').get()
        url = response.url
        filing_date = datetime.date.today().isoformat()

        if year >= '2009':
            # Download the source page
            path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f'{report_name}.html')
            write_source_doc(path, response.body)

            # Parse the report
            # Write meta data
            meta_data = {
                report_name: {FULL_TITLE: title, FILING_DATE: filing_date, URL: url}
            }
            path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f"{report_name}.json")
            write_meta(path, meta_data)