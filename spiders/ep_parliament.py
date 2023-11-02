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
COUNTRY = 'ep'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'


class EpParliamentSpider(scrapy.Spider):
    name = 'ep'
    # handle_httpstatus_list = [200]

    def __init__(self, **kwargs) -> None:
        self.start_urls = []

        # Define the end dates of the legislative periods
        # This is required for URL construction
        legislative_period_list = [(8, datetime.date(2019, 4, 18)), (9, datetime.date(2019, 12, 31))]
        date_dict = {}
        # Contstruct URLs to query
        for index, value in enumerate(legislative_period_list):
            legislative_period = value[0]
            date = value[1]
            if index == 0:
                start_date = datetime.date(2017, 7, 7)
            else:
                # Get the day after the end date of the legislative period
                start_date = legislative_period_list[index - 1][1] + datetime.timedelta(1)
            delta = date - start_date
            date_dict[legislative_period] = [start_date + datetime.timedelta(days=i) for i in range(delta.days + 1)]

        # Construct the URLs
        for legislative_period, date_list in date_dict.items():
            for date in date_list:
                self.start_urls.append(f'https://www.europarl.europa.eu/doceo/document/CRE-{legislative_period}-{date.isoformat()[:10]}_EN.html')
        # Slight misuse of the function, but should do the job
        prepare_folder_national(DATA, COUNTRY, NATIONAL)
        super().__init__(**kwargs)

    def start_requests(self):
        meta = {'dont_redirect': True}
        for url in self.start_urls:
            yield Request(url, callback=self.parse, meta=meta)

    def parse(self, response, **kwargs):

        # Get meta data
        url = response.url
        filing_date = datetime.date.today().isoformat()
        url_splitted = url.split('_')[0]
        title = url_splitted.split('/')[-1]
        legislative_period = title.split("-")[1]
        date = title[-10:]
        year = date[:4]
        report_name = title

        # Download the source page
        path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f'{report_name}.html')
        write_source_doc(path, response.body)

        # Parse the report
        # Write meta data
        meta_data = {
            report_name: {FULL_TITLE: title, FILING_DATE: filing_date, URL: url, "legislative_period": legislative_period}
        }
        path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f"{report_name}.json")
        write_meta(path, meta_data)