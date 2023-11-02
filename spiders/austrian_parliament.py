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
COUNTRY = 'austria'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'


class AustriaParliamentSpider(scrapy.Spider):
    name = COUNTRY
    start_urls = []

    def __init__(self, **kwargs) -> None:
        # Do the api call to the open data api of ireland
        self.urls = []
        base_url = 'https://www.parlament.gv.at'
        for gp in ['XXVI', 'XXVII']:
            resp = requests.get(f'https://www.parlament.gv.at/filter.psp?view=xml&FBEZ=FP_011&R_NBVS=N&GP={gp}')
            if resp.status_code != 200:
                raise AssertionError
            # Get the results and retrieve the URLs for the HTML documents
            xml = etree.fromstring(resp.content)
            item_list = xml.xpath('//item')
            for item in item_list:
                date = item.xpath('./Datum/text()')[0]
                date = re.sub('\s', '', date)
                date = datetime.datetime.strptime(date, '%d.%m.%Y')
                # Get the number for naming the documents
                session = item.xpath('./Sitzung/text()')[0]
                # Only get the required docs
                if date < datetime.datetime.strptime('14.12.2018', '%d.%m.%Y'):
                    break
                session = re.sub('\s', '', session)
                number = re.search('\d+(?=.)', session).group()
                try:
                    # Get the URL of the protocol
                    uri = item.xpath('./Gesamtprotokoll//a[contains(@href, ".html")]/@href')[0]
                except IndexError:
                    # Protocol not yet available
                    continue
                url = base_url + uri
                self.urls.append({'url': url, 'date': date, 'number': number})
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

        # Get date, year, number+
        date = response.meta["date"]
        year = date.strftime("%Y")
        number = str(response.meta["number"])

        # Build the report name from the date and the chamber
        report_name = "_".join([REPORT, number])

        # Download the source page
        path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f'{report_name}.html')
        write_source_doc(path, response.body)

        # Parse the report
        # Write meta data
        meta_data = {
            report_name: {FULL_TITLE: report_name, FILING_DATE: filing_date, URL: url}
        }
        path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f"{report_name}.json")
        write_meta(path, meta_data)