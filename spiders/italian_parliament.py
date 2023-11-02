import pathlib
import scrapy
import locale
import datetime

from .utils import (
    prepare_folder_national,
    write_meta,
    write_source_doc,
)

ROOT = pathlib.Path(__file__).absolute().parent
DATA = ROOT.joinpath("data")

# Define string constants
COUNTRY = 'italy'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'


class ItalianParliamentSpider(scrapy.Spider):
    name = "italy"

    def __init__(self, **kwargs) -> None:
        # Hard code upper limits for sittings per legislation, as API is fully in Italian
        # legis_sitting_pair = {18: 552, 17: 906, 16: 740}
        legis_sitting_pair = {16: 740}
        self.start_urls = []
        for key, value in legis_sitting_pair.items():
            for sitting in range(1, value):
                self.start_urls.append(f"https://documenti.camera.it/apps/resoconto/getXmlStenografico.aspx?idNumero={sitting}&idLegislatura={key}")

        prepare_folder_national(DATA, COUNTRY)
        super().__init__(**kwargs)

    def parse(self, response, **kwargs):

        year = response.xpath('//seduta/@anno').get()
        year = year.strip()
        if int(year) > 2008:
            month = response.xpath('//seduta/@mese').get()
            month = month.strip()
            day = response.xpath('//seduta/@giorno').get()
            day = day.strip()
            sitting_number = response.xpath('//seduta/@numero').get()

            # Get meta data
            url = response.url
            filing_date = datetime.date.today().isoformat()
            title = year + month + day + "_" + sitting_number + "_" + REPORT
            report_name = title

            # Download the source page
            path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f'{report_name}.xml')
            write_source_doc(path, response.body)

            # Parse the report
            # Write meta data
            meta_data = {
                report_name: {FULL_TITLE: title, FILING_DATE: filing_date, URL: url}
            }
            path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f"{report_name}.json")
            write_meta(path, meta_data)

