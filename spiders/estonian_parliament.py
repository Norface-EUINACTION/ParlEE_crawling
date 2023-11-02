import pathlib
import scrapy
import datetime

from scrapy.linkextractors import LinkExtractor
from .utils import (
    prepare_folder_national,
    write_meta,
    write_source_doc,
)

ROOT = pathlib.Path(__file__).absolute().parent
DATA = ROOT.joinpath("data")

# Define string constants
COUNTRY = 'estonia'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'


class EstonianParliamentSpider(scrapy.Spider):
    name = 'estonia'
    start_urls = [
        'https://stenogrammid.riigikogu.ee/et?rangeFrom=01.01.2009&rangeTo=31.12.2020&singleDate=&phrase=&type=ALL'
    ]

    def __init__(self, **kwargs) -> None:
        self.le_documents = LinkExtractor(
            restrict_xpaths='(//a[@class="istungLink"])')
        self.le_next_page = LinkExtractor(
            restrict_xpaths='(//a[@class="page-link"])[2]')
        prepare_folder_national(DATA, COUNTRY)
        super().__init__(**kwargs)

    def parse(self, response, **kwargs):
        # Start URLs lead to the overview page of a legislative period
        # Go through all documents/rows of the legislative period and download them
        rows = response.xpath('//tr[@class = "accordion-clickable open"]')

        document_links = self.le_documents.extract_links(response)
        next_page_links = self.le_next_page.extract_links(response)

        # Go to next page
        yield from response.follow_all(
            next_page_links,
            callback=self.parse,
            **kwargs
        )

        for i, row in enumerate(rows):

            # Get the topic of the session
            topic = row.xpath('./td[2]/a/text()').get()
            title = topic.strip('\t\n\r ')
            topic = str.lower(topic.split(",")[-1].strip('\t\n\r ').replace(" ", "_"))

            # Get an parse the date
            date_elem = row.xpath('./td[1]/text()').get()
            date_elem = str.lower(date_elem.split("/")[0].strip('\t\n\r ').replace(' ', ''))
            # Set locale to Belgium in order to parse Belgian dates
            date = datetime.datetime.strptime(date_elem, '%d.%m.%Y')
            year = str(date.year)
            date = date.strftime('%Y%m%d')
            # These years are not required
            if year < '2009':
                continue

            # Build the meta data
            report_name = f'{date}_{topic}'
            title = f'{date} {title}'

            # Follow the
            yield response.follow(
                document_links[i],
                callback=self.parse_report,
                meta={'title': title, 'report_name': report_name, 'year': year},
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

