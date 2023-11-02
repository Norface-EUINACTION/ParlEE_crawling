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
COUNTRY = 'belgium'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'


class BelgianParliamentSpider(scrapy.Spider):
    name = "belgium"
    start_urls = [
        'https://www.dekamer.be/kvvcr/showpage.cfm?section=/cricra&language=nl&cfm=dcricra.cfm?type=plen&cricra=CRA&count=all&legislat=55',
        'https://www.dekamer.be/kvvcr/showpage.cfm?section=/cricra&language=nl&cfm=dcricra.cfm?type=plen&cricra=CRA&count=all&legislat=54',
        'https://www.dekamer.be/kvvcr/showpage.cfm?section=/cricra&language=nl&cfm=dcricra.cfm?type=plen&cricra=CRA&count=all&legislat=53',
        'https://www.dekamer.be/kvvcr/showpage.cfm?section=/cricra&language=nl&cfm=dcricra.cfm?type=plen&cricra=CRA&count=all&legislat=52'
    ]

    def __init__(self, **kwargs) -> None:
        prepare_folder_national(DATA, COUNTRY)
        super().__init__(**kwargs)

    def parse(self, response, **kwargs):
        # Start URLs lead to the overview page of a legislative period
        # Go through all documents/rows of the legislative period and download them
        rows = response.xpath('//tr')

        for row in rows:
            # get the session id
            session_id = row.xpath('./td[1]/a/text()').get()
            session_id = session_id.strip('\t\n\r ')

            # Get the topic of the session
            topic = row.xpath('./td[2]/i/text()').get()
            topic = str.lower(topic.strip('\t\n\r ').replace(' ', ''))

            # Get an parse the date
            date_elem = row.xpath('./td[3]//text()').get()
            date_elem = str.lower(date_elem.strip('\t\n\r ').replace(' ', ''))
            # Set locale to Belgium in order to parse Belgian dates
            locale.setlocale(locale.LC_TIME, 'nl_BE')
            date = datetime.datetime.strptime(date_elem, '%d%B%Y')
            year = str(date.year)
            date = date.strftime('%Y%m%d')
            # These years are not required
            if year < '2009':
                continue

            # Get the link to the report
            rel_doc_link = row.xpath('./td[4]/a/@href').get()

            # Build the meta data
            report_name = f'{session_id}_{REPORT}'
            title = f'{date}_{topic}'

            yield response.follow(
                rel_doc_link,
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
        path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f'{report_name}.pdf')
        write_source_doc(path, response.body)

        # Parse the report
        # Write meta data
        meta_data = {
            report_name: {FULL_TITLE: title, FILING_DATE: filing_date, URL: url}
        }
        path = DATA.joinpath(NATIONAL, COUNTRY, year, SOURCE, f"{report_name}.json")
        write_meta(path, meta_data)

