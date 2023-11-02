import pathlib
import scrapy
import datetime
import re

from scrapy.linkextractors import LinkExtractor
from .utils import (
    prepare_folder_national,
    write_meta,
    write_source_doc,
)

ROOT = pathlib.Path(__file__).absolute().parent
DATA = ROOT.joinpath("data")

# Define string constants
COUNTRY = 'malta'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'


class MalteseParliamentSpider(scrapy.Spider):
    name = 'malta'
    start_urls = [
        'https://parlament.mt/en/11th-leg/plenary-session/?type=committeedocuments',
        'https://parlament.mt/en/12th-leg/plenary-session/?type=committeedocuments',
        'https://parlament.mt/en/13th-leg/plenary-session/?type=committeedocuments',
    ]

    def __init__(self, **kwargs) -> None:
        self.le_documents = LinkExtractor(
            restrict_xpaths='//a[contains(text(), "Transcript")]')
        prepare_folder_national(DATA, COUNTRY)
        super().__init__(**kwargs)

    def parse(self, response, **kwargs):
        rows = response.xpath('//a[contains(text(), "Transcript")]/parent::td/parent::tr')

        for i, row in enumerate(rows):

            # Get the topic of the session
            info_raw = row.xpath('./td[1]/a/text()').get()
            # Parse the information
            info_raw_list = info_raw.split()
            sitting_no = info_raw_list[0]
            sitting_no = sitting_no.strip()
            date_raw = info_raw_list[2]
            date_raw = date_raw.strip()
            date = datetime.datetime.strptime(date_raw, '%d/%m/%Y')
            legislation = re.search('\d{2}', response.url).group()

            # These years are not required
            if date.year < 2009:
                continue

            document_link = row.xpath('./td[4]/a/@href').get()

            # Build the meta data
            report_name = f'{date.isoformat()[:10]}_{legislation}_{sitting_no}'
            title = f'{date.isoformat()[:10]}_{legislation}_{sitting_no}'

            # Follow the
            yield response.follow(
                document_link,
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
        path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f'{report_name}.doc')
        write_source_doc(path, response.body)

        # Parse the report
        # Write meta data
        meta_data = {
            report_name: {FULL_TITLE: title, FILING_DATE: filing_date, URL: url}
        }
        path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f"{report_name}.json")
        write_meta(path, meta_data)
