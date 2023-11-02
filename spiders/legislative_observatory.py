import pathlib
import scrapy
from lxml.html import soupparser
from scrapy.http.request import Request
import datetime
import pandas as pd
import glob

from .utils import (
    parse_url,
    write_txt,
    prepare_folder_eu,
    write_meta,
    normalize_name,
    write_source_doc,
)

ROOT = pathlib.Path(__file__).absolute().parent
DATA = ROOT.joinpath("data")

# Define string constants
# Constants are used to identify the corresponding events on European Observatory
KEY_EVENT_IDENTIFICATION = {
    'Legislative proposal': 'COM',
    'Committee report': 'A',
    'Council position': 'Council position',
}
EVENT_TYPE = 'event_type'
FINAL_ACT_TITLE = 'Final act 1'
FINAL_ACT_EVENT = 'Final act'
URL = 'URL'
DOC_TYPE = 'doc_type'
TITLE = 'title'
UID = 'uid'
FULL_TITLE = 'full_title'
CELEX = 'celex'
FILING_DATE = 'filing_date'
SUMMARY = 'sum'
FULL = 'full'
SOURCE = 'source'
SUFFIX_DOC = 'suffix_doc'
PARSED_TEXT = 'parsed_text'
NUMBER = 'number'
EU = 'eu'

EURLEX_URL_PREFIX = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX%3A"


# print(f'{ROOT=}')
# print(f'{DATA=}')
class LegislativeObservatorySpider(scrapy.Spider):
    name = "eu"
    base_url = "https://oeil.secure.europarl.europa.eu"
    start_urls = []

    def __init__(self, input: str, get_summaries=False, get_full=False) -> None:
        self.identifiers = []
        self.council_positions_url = {}
        self.get_summaries = get_summaries
        self.get_full = get_full
        # Read procedure data (only works if there is a single .xls file, should be the latest from Leiden)
        # When in doubt double check NextCloud, folder EurLex_data
        data = pd.read_excel(glob.glob(input + '/*.xls')[0],
                             usecols=["procedure_ref1", "cn_pref_link"])
        # Handling of erroneous and empty entries in .xls
        data.cn_pref_link.replace(to_replace='\\xa0', value='', regex=True, inplace=True)
        data.cn_pref_link.fillna('', inplace=True)
        for _, row in data.iterrows():
            # Get procedure ids
            uid = row.procedure_ref1.strip()
            prepare_folder_eu(DATA, uid, summary=SUMMARY, full=FULL)
            self.identifiers.append(uid)
            # In some cases there are multiple council positions
            self.council_positions_url[uid] = row.cn_pref_link.strip().split()
        # Get rid of the data object
        del data
        # self.start_urls.append("https://oeil.secure.europarl.europa.eu/oeil/popups/ficheprocedure.do?reference=2017/0224(COD)&l=en")
        # self.start_urls.append("https://oeil.secure.europarl.europa.eu/oeil/popups/ficheprocedure.do?reference=2007/0286(COD)&l=en")

        # Only used for debugging
        # self.identifiers = ['2017/0017(COD)']

    def start_requests(self) -> Request:
        for uid in self.identifiers:
            url = f"https://oeil.secure.europarl.europa.eu/oeil/popups/ficheprocedure.do?reference={uid}&l=en"
            yield Request(url, callback=self.parse, meta={UID: uid})

    def parse(self, response, **kwargs):

        # get identifier in scope
        uid = response.meta[UID]

        # parse tables
        key_events_data = response.xpath('//div[@id="key_events-data"]')
        final_act_data = response.xpath('//div[@id="final_act-data"]')

        # Get relevant key events and collect summary links and full document links
        summaries = {}
        full = {}
        for key_event_type, xpath_identifier in KEY_EVENT_IDENTIFICATION.items():
            # Council position (identified by string in second column)
            if key_event_type == 'Council position':
                rel_key_event_rows = key_events_data.xpath(
                    f'.//span[contains(text(), "{xpath_identifier}")]/text()/ancestor::div[@class="ep-table-row"]')
            # Rest (identified by characteristics of third column) ==> Normalize space to get rid of spaces
            else:
                rel_key_event_rows = (key_events_data.xpath(
                    f'.//div[@class="ep-table-row"]/div[3]/div//*[starts-with(normalize-space(), "{xpath_identifier}")]/ancestor::div[@class="ep-table-row"]'))
                # Some leglislative proposals are named differently
                # ==> Fall back to the title of the legislative proposal
                if key_event_type == 'Legislative proposal' and not rel_key_event_rows:
                    rel_key_event_rows = (key_events_data.xpath(
                        f'.//div[@class="ep-table-row"]/div[2]/div//*[starts-with(normalize-space(), "Legislative proposal")]/ancestor::div[@class="ep-table-row"]'))
                    # Summary of legislative proposal must be there
                    if not rel_key_event_rows:
                        raise AssertionError

            # Will get multiple rows if there are updates on a document
            for i, row in enumerate(rel_key_event_rows):
                # Get full title from second column
                # Assumes that the title is unique
                key_event_title = row.xpath(f'./div[2]/div/span/text()').get()
                # Create nested dict for summaries and full texts
                # {'Legislative proposal published':
                #                                   {EVENT_TYPE: 'Legislative proposal'},
                #                                   {'URL': https://...},
                #                                   {NUMBER: 1}
                # }
                # Add a number to the title in case the titles appear multiple times
                key_event_title = key_event_title + ' ' + str(i + 1)
                # Collect summaries, if it exists
                if bool(row.xpath(".//button/@onclick")):
                    summaries[key_event_title] = {}
                    summaries[key_event_title][EVENT_TYPE] = key_event_type
                    summaries[key_event_title][URL] = parse_url(row.xpath(".//button/@onclick").get())
                    summaries[key_event_title][NUMBER] = str(i + 1)
                # Council position URL is read from excel, rest from website
                if key_event_type == "Council position":
                    continue

                # Collect full documents
                full[key_event_title] = {}
                full[key_event_title][EVENT_TYPE] = key_event_type
                if (key_event_type == 'Legislative proposal') & bool(
                        row.xpath('.//a[@class="tiptip eurLex"]/@href').get()):
                    # Use eurLex if possible as it offers html version of document
                    # Build CELEX number
                    # (more information check https://eur-lex.europa.eu/content/help/faq/celex-number.html?locale=de)
                    # CELEX identifies a document uniquely
                    # <Sector><Year><Doc Type><Doc Nr.> ==> e.g. 52013PC0796
                    # Sector of proposals
                    sector = "5"
                    # Get the document year from the URL
                    year = row.xpath(
                        'substring-before(substring-after(.//a[@class="tiptip eurLex"]/@href, "an_doc="), "&")').get()
                    # Doc type of proposals
                    doc_type = "PC"
                    # Get the document number from the URL ==> It is always 4 digits
                    doc_num = row.xpath('substring-after(.//*[contains(text(), "COM(")]/text(), ")")').get()[:4]
                    celex_num = sector + year + doc_type + doc_num

                    full[key_event_title][URL] = EURLEX_URL_PREFIX + celex_num
                else:
                    full[key_event_title][URL] = row.xpath('.//a[@class="externalDocument"]/@href').get()
                if full[key_event_title][URL] is None:
                    full[key_event_title][URL] = ''
                full[key_event_title][NUMBER] = str(i + 1)

        # Add full council positions URL from .xls input file
        for i, council_position_url in enumerate(self.council_positions_url.get(uid)):
            full[f'Council position {i + 1} published'] = {}
            full[f'Council position {i + 1} published'][EVENT_TYPE] = 'Council position'
            full[f'Council position {i + 1} published'][URL] = council_position_url

        # Get final act
        # Summary
        if bool(final_act_data.xpath(".//button/@onclick")):
            summaries[FINAL_ACT_TITLE] = {}
            summaries[FINAL_ACT_TITLE][EVENT_TYPE] = FINAL_ACT_EVENT
            summaries[FINAL_ACT_TITLE][URL] = parse_url(final_act_data.xpath(".//button/@onclick").get())
        # Full
        if bool(final_act_data.xpath('.//a[1]/@href').get()):
            full[FINAL_ACT_TITLE] = {}
            full[FINAL_ACT_TITLE][EVENT_TYPE] = FINAL_ACT_EVENT
            celex_num = final_act_data.xpath(
                'substring-after(//div[@id="final_act-data"]//a[1]/@href, "numdoc=")').get()
            full[FINAL_ACT_TITLE][URL] = EURLEX_URL_PREFIX + celex_num

        # Get summaries
        if self.get_summaries:
            for title, meta_infos in summaries.items():
                yield Request(
                    meta_infos.get(URL),
                    callback=self.parse_summary,
                    meta={TITLE: title, UID: uid, EVENT_TYPE: meta_infos.get(EVENT_TYPE), DOC_TYPE: SUMMARY,
                          NUMBER: meta_infos.get(NUMBER)},
                    **kwargs,
                )

        # Get full docs
        if self.get_full:
            for title, meta_infos in full.items():
                # Separate processing for different types of full documents
                meta_full = {TITLE: title, UID: uid, EVENT_TYPE: meta_infos.get(EVENT_TYPE), DOC_TYPE: FULL,
                             NUMBER: meta_infos.get(NUMBER)}
                url = meta_infos.get(URL)
                # In case there is no council position, the URL is not filled
                if url != '':
                    # .pdf documents (council position)
                    if 'Council position' in meta_infos.get(EVENT_TYPE):
                        yield Request(
                            url,
                            callback=self.parse_council_position,
                            meta=meta_full,
                            **kwargs,
                        )
                    # EP committee reports
                    elif meta_infos.get(EVENT_TYPE) == 'Committee report':
                        yield Request(
                            url,
                            callback=self.parse_committee_report_full,
                            meta=meta_full,
                            **kwargs,
                        )
                    # Final act and legislative proposal
                    elif 'eur-lex.europa.eu' in url:
                        yield Request(
                            url,
                            callback=self.parse_proposal_and_final_act_full,
                            meta=meta_full,
                            **kwargs,
                        )

    def parse_summary(self, response):
        """
        Parses the summaries of legislative proposals, committee reports, council positions or final acts.
        Downloads:
        - The parsed legislative proposal, committee report, council position or final act
        - The original legislative proposal, committee report, council position or final act
        - Meta data
        """

        # Get main text (using soupparser to benefit from opinionated guess on bad html)
        body = response.text.strip().replace("\x00", "").encode("utf8")
        root = soupparser.fromstring(body)
        if bool(root.xpath("//div[@class='ep-a_text']//*[@class='MsoNormal']")):
            text = root.xpath("//div[@class='ep-a_text']//*[@class='MsoNormal']")
            text = [x.xpath("normalize-space()") for x in text]
        else:
            # Quick fix to handle differently structured summaries
            text = root.xpath("//div[@class='ep-a_text']/child::*//text()")
            text = [x.strip('\n\r\t ') for x in text]
        text = " ".join(text)
        text = text.replace('\n', ' ')

        # Write source document
        response.meta[SUFFIX_DOC] = '.html'
        self.download_document(response, is_full_doc=False, is_parsed=False)

        # Write main text
        response.meta[SUFFIX_DOC] = '.txt'
        response.meta[PARSED_TEXT] = text
        self.download_document(response, is_full_doc=False, is_parsed=True)

    def parse_committee_report_full(self, response):
        """
        Parses the EP committee report.
        Downloads:
        - The parsed EP committee report
        - The original EP committee report
        - Meta data
        """

        # Write source document
        response.meta[SUFFIX_DOC] = '.html'
        self.download_document(response, is_full_doc=True, is_parsed=False)

        # todo: Implement parsing for committee report full

    def parse_proposal_and_final_act_full(self, response):
        """
        Parses the legislative proposals or final acts.
        Downloads:
        - The parsed legislative proposal or final act.
        - The original legislative proposal ot final act
        - Meta data
        """

        # Write source document
        response.meta[SUFFIX_DOC] = '.html'
        self.download_document(response, is_full_doc=True, is_parsed=False)

        # todo: Implement parsing for final act and legislative proposal full

    def parse_council_position(self, response):
        """
        Parses the .pdf-document containing the council position.
        Download:
        - The parsed council position
        - The original council position
        - Meta data
        """

        # Write source document
        response.meta[SUFFIX_DOC] = '.pdf'
        self.download_document(response, is_full_doc=True, is_parsed=False)

        # todo: Implement parsing for council position full

    def download_document(self, response, is_full_doc: bool, is_parsed: bool):

        # Get meta data
        uid = response.meta[UID]
        title = response.meta[TITLE]
        # Remove the number from the title which was a workaround to store the data in the dict
        title = title[:-2]
        normalized_title = normalize_name(title=title, event_type=response.meta[EVENT_TYPE],
                                          doc_type=response.meta[DOC_TYPE], number=response.meta.get(NUMBER))
        filing_date = datetime.date.today().isoformat()
        url = response.url
        suffix_doc = response.meta[SUFFIX_DOC]

        # Construct file path for writing the document
        file_name = normalized_title + suffix_doc
        if is_full_doc & (not is_parsed):
            path = DATA.joinpath(EU, uid, FULL, SOURCE, file_name)
        elif is_full_doc & is_parsed:
            path = DATA.joinpath(EU, uid, FULL, file_name)
        elif (not is_full_doc) & (not is_parsed):
            path = DATA.joinpath(EU, uid, SUMMARY, SOURCE, file_name)
        else:
            path = DATA.joinpath(EU, uid, SUMMARY, file_name)

        # Write document
        if is_parsed:
            text = response.meta[PARSED_TEXT]
            # Write the parsed document
            write_txt(path, text)
        else:
            # Write the unparsed/source document
            write_source_doc(path, response.body)

        # Write meta data
        meta_data = {
            normalized_title: {FULL_TITLE: title, FILING_DATE: filing_date, URL: url}
        }

        # Extract celex number from URL
        if is_full_doc \
                and response.meta.get('event_type') != 'Committee report' \
                and response.meta.get('event_type') != 'Council position':
            celex = url.split('%3A')[1]
            # Add celex number if available
            meta_data[normalized_title][CELEX] = celex

        if is_full_doc:
            path = DATA.joinpath(EU, uid, FULL, SOURCE, f"{normalized_title}.json")
        else:
            path = DATA.joinpath(EU, uid, SUMMARY, SOURCE, f"{normalized_title}.json")
        write_meta(path, meta_data)
