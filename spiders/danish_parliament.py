import pathlib
import scrapy
from eia_crawling.spiders.utils import prepare_folder_national, write_source_doc, write_meta, normalize_string
import re
import datetime

ROOT = pathlib.Path(__file__).absolute().parent
DATA = ROOT.joinpath("data")

COUNTRY = 'denmark'
REPORT = 'meeting'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
NATIONAL = 'national'


class DannishParlimentSpider(scrapy.Spider):
    name = 'denmark'
    allowed_domain = 'https://www.ft.dk/da/dokumenter/dokumentlister/referater?'

    def __init__(self, start_date=None, end_date=None, **kwargs) -> None:
        # Call to init superclass method
        prepare_folder_national(DATA, COUNTRY)

        # Allow for date range specification
        self.start_date = datetime.datetime.strptime(start_date, '%d-%m-%Y')
        self.end_date = datetime.datetime.strptime(end_date, '%d-%m-%Y')

        self.start_urls = ['https://www.ft.dk/da/dokumenter/dokumentlister/referater?startDate='
                      + str(self.start_date.year) + '%02d' % self.start_date.month + '%02d' % self.start_date.day
                      + '&endDate=' + str(self.end_date.year) + '%02d' % self.end_date.month + '%02d' % self.end_date.day]

        super().__init__(**kwargs)

    def parse(self, response, **kwargs):

        rows = response.xpath("//tr[@class='listespot-wrapper__data-item']")

        for row in rows:
            # Get and parse the date of the report
            date = row.xpath('./td[1]/a/p/text()').get()
            date = date.split()[0]
            date = datetime.datetime.strptime(date, '%d.%m.%Y')
            year = str(date.year)

            # Get topic
            topic = normalize_string(row.xpath('./td[2]/a/p/text()').get())  # e.g. '89th meeting on Tuesday'

            # Get meeting number (will serve as identifier)
            meeting_id = topic.split()[0]  # e.g. '89th'
            meeting_id = re.sub('[^0-9]', '', meeting_id)  # e.g. '89'

            # Get the link to the report
            link_to_report = f"https://www.ft.dk/{row.xpath('./td[1]/a/@href').get()}"
            # Build metadata for each response
            report_name = f'{meeting_id}_{REPORT}'
            title = f'{date}_{topic}'

            yield response.follow(
                link_to_report,
                callback=self.parse_report,
                meta={'title': title, 'report_name': report_name, 'year': year},
                **kwargs
            )

        # Handle pagination
        next_page = response.xpath("//ul[@class='pagination pagination-centered text-center']/li[@class='next']/a/@href").get()
        if next_page is not None:
            yield response.follow(next_page, callback=self.parse)

    def parse_report(self, response):

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

