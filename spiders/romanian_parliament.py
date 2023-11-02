import pathlib
import scrapy
import datetime

from scrapy import Request
from scrapy.linkextractors import LinkExtractor
from .utils import (
    prepare_folder_national,
    write_meta,
    write_source_doc,
    normalize_string
)

ROOT = pathlib.Path(__file__).absolute().parent
DATA = ROOT.joinpath("data")

# Define string constants
COUNTRY = 'romania'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'


class RomanianParliamentSpider(scrapy.Spider):
    name = 'romania'
    # handle_httpstatus_list = [500, 502]

    def __init__(self, **kwargs) -> None:
        self.start_urls = []
        for year in range(2009, 2020):
            self.start_urls.append(f'http://www.cdep.ro/pls/steno/steno.calendar?cam=2&an={year}&idl=1')
        self.le_calender = LinkExtractor(
            restrict_xpaths='(//a[contains(@href, "steno/steno.data")]')
        prepare_folder_national(DATA, COUNTRY)
        super().__init__(**kwargs)

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, callback=self.parse)

    def parse(self, response, **kwargs):
        # Parse the calender
        calender_links = self.le_calender.extract_links(response)

        # Go to next page
        yield from response.follow_all(
            calender_links,
            callback=self.parse,
            **kwargs
        )

    def parse_single_sitting(self, response, **kwargs):

        steno_link = response.xpath('//a[contains(text(), "complet")]/@href').get()

        # Get the topic of the session
        # Parse the information
        date_raw_list = response.xpath('//td[@class="cale2"]//text()').getall()
        date_raw = " ".join(date_raw_list)
        date_raw = date_raw.split('>')[-1]
        if date_raw:
            date_raw = date_raw.strip()
            date = datetime.datetime.strptime(date_raw, '%d-%m-%Y')

        # Build the meta data
        report_name = date.isoformat()[:10] + "_" + "sitting"
        title_raw = response.xpath('//span[@class="headline"]/text()').get()
        title = normalize_string(title_raw)
        title = title.strip()

        # Follow the
        yield response.follow(
            steno_link,
            callback=self.parse_report,
            meta={'title': title, 'report_name': report_name, 'year': str(date.year)},
            **kwargs
        )

    def parse_report(self, response, **kwargs):

        # Get meta data
        url = response.url
        filing_date = datetime.date.today().isoformat()
        year = response.meta.get("year")
        title = response.meta.get("title")
        report_name = response.meta.get("report_name")

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
