import numpy as np
import pathlib
from eia_crawling.parsing.parsing_french_parliament import parse_french_parliament
from eia_crawling.parsing.parsing_german_parliament import parse_german_parliament
from eia_crawling.parsing.parsing_irish_parliament import parse_irish_parliament
from eia_crawling.parsing.parsing_belgian_parliament import parse_belgian_parliament
from eia_crawling.parsing.parsing_austrian_parliament import parse_austrian_parliament
from eia_crawling.parsing.parsing_danish_parliament import parse_danish_parliament
from eia_crawling.parsing.parsing_hungarian_parliament import parse_hungarian_parliament
from eia_crawling.parsing.parsing_lithuanian_parliament import parse_lithuanian_parliament
from eia_crawling.parsing.parsing_estonian_parliament import parse_estonian_parliament
from eia_crawling.parsing.parsing_swedish_parliament import parse_swedish_parliament
from eia_crawling.parsing.parsing_portuguese_parliament import parse_portuguese_parliament
from eia_crawling.parsing.parsing_polish_parliament import parse_polish_parliament
from eia_crawling.parsing.parsing_romanian_parliament import parse_romanian_parliament
from eia_crawling.parsing.parsing_bulgarian_parliament import parse_bulgarian_parliament
from eia_crawling.parsing.parsing_slovakian_parliament import parse_slovakian_parliament
from eia_crawling.parsing.parsing_uk_parliament import parse_uk_parliament
from eia_crawling.parsing.parsing_ep_parliament import parse_ep_parliament
from eia_crawling.parsing.parsing_cypriot_parliament import parse_cypriot_parliament
from eia_crawling.parsing.parsing_greek_parliament import parse_greek_parliament
from eia_crawling.parsing.parsing_finnish_parliament import parse_finnish_parliament
from eia_crawling.parsing.parsing_maltese_parliament import parse_maltese_parliament
from argparse import ArgumentParser

SOURCE = 'source'
SPIDERS = 'spiders'
DATA = 'data'
NATIONAL = 'national'


def main(country: str,
         year: int = None):
    """
    Parse the national parliamentary speeches
    """

    # Get the path to the national folder
    current_p = pathlib.Path(__file__).absolute().parent.parent
    root_p = current_p.joinpath(SPIDERS, DATA, NATIONAL, country)

    # Default years:
    if year is None:
        years = list(np.arange(2009, 2022))
    else:
        years = [year]

    # Iterate through the years
    for year in years:
        print(f'Started with {root_p.stem} {year}')
        current_year_p = root_p.joinpath(str(year))
        current_year_source_p = root_p.joinpath(str(year), 'source')
        # Make sure source folder exists
        if current_year_source_p.is_dir():
            # Get the path to all html documents in the source folder
            if country == 'france' or country == 'austria' or country == 'denmark' or country == 'hungary' or country == 'lithuania' or country == 'estonia' or country == 'romania' or country == 'bulgaria' or country == 'united_kingdom' or country == 'sweeden':
                source_files_p = current_year_source_p.glob('*.html')
            # Get the path to XML documents
            elif country == 'germany' or country == 'ireland' or country == 'ep':
                source_files_p = current_year_source_p.glob('*.xml')
            elif country == 'belgium' or country == 'portugal' or country == 'finland':
                source_files_p = current_year_source_p.glob('*.pdf')
            elif country == 'malta':
                source_files_p = current_year_source_p.glob('*.doc')
            elif country == 'poland':
                source_files_p = current_year_source_p.glob('*text_structure.xml')
                meta_files_p = list(current_year_source_p.glob('*header.xml'))
            elif country == 'slovakia' or country == 'greece':
                source_files_p = current_year_source_p.glob('*.docx')
            elif country == 'cyprus':
                source_files_p = current_year_source_p.glob('*.txt')
            for i, source_file_p in enumerate(source_files_p):
                # Call the national specific parser
                if country == 'france':
                    meta_file_p = source_file_p.with_suffix('.json')
                    parse_french_parliament(year_path=current_year_p,
                                            year=year,
                                            source_html_path=source_file_p,
                                            meta_json_path=meta_file_p)
                elif country == 'germany':
                    parse_german_parliament(year_path=current_year_p,
                                            year=year,
                                            source_xml_path=source_file_p)
                elif country == 'ireland':
                    parse_irish_parliament(year_path=current_year_p,
                                           year=year,
                                           source_xml_path=source_file_p)
                elif country == 'belgium':
                    # call specific docs for testing
                    # source_file_p = source_file_p.parent.joinpath('0284_session.pdf')
                    meta_file_p = source_file_p.with_suffix('.json')
                    parse_belgian_parliament(year_path=current_year_p,
                                             year=year,
                                             source_pdf_path=source_file_p,
                                             meta_json_path=meta_file_p)
                elif country == 'austria':
                    # Call specific sessions for testing
                    # source_file_p = source_file_p.parent.joinpath('session_72.html')
                    meta_file_p = source_file_p.with_suffix('.json')
                    parse_austrian_parliament(year_path=current_year_p,
                                              year=year,
                                              source_html_path=source_file_p,
                                              meta_json_path=meta_file_p)

                elif country == 'denmark':
                    parse_danish_parliament(year_path=current_year_p,
                                            year=year,
                                            source_html_path=source_file_p)

                elif country == 'hungary':
                    parse_hungarian_parliament(year_path=current_year_p,
                                               year=year,
                                               source_html_path=source_file_p)
                elif country == 'lithuania':
                    # source_file_p = source_file_p.parent.joinpath("Seimo rytinio plenarinio posėdžio Nr. 447 stenograma.html")
                    parse_lithuanian_parliament(year_path=current_year_p,
                                                year=year,
                                                source_html_path=source_file_p)
                elif country == 'estonia':
                    meta_file_p = source_file_p.with_suffix('.json')
                    parse_estonian_parliament(year_path=current_year_p,
                                              year=year,
                                              source_html_path=source_file_p,
                                              meta_json_path=meta_file_p)
                elif country == 'portugal':
                    parse_portuguese_parliament(year_path=current_year_p,
                                                year=year,
                                                source_pdf_path=source_file_p)
                elif country == 'poland':
                    meta_file_p = meta_files_p[i]
                    parse_polish_parliament(year_path=current_year_p,
                                            year=year,
                                            source_xml_path=source_file_p,
                                            meta_xml_path=meta_file_p)
                elif country == 'romania':
                    # source_file_p = source_file_p.parent.joinpath("Şedinţa Camerei Deputaţilor din 2 martie 2009.html")
                    parse_romanian_parliament(year_path=current_year_p,
                                              year=year,
                                              source_html_path=source_file_p)
                elif country == 'slovakia':
                    # source_file_p = source_file_p.parent.joinpath("Şedinţa Camerei Deputaţilor din 2 martie 2009.html")
                    parse_slovakian_parliament(year_path=current_year_p,
                                               year=year,
                                               source_doc_path=source_file_p)
                elif country == 'bulgaria':
                    # source_file_p = source_file_p.parent.joinpath("ТРИСТА СЕДЕМДЕСЕТ И ПЕТО ЗАСЕДАНИЕ София, петък, 13 юли 2012.html")
                    parse_bulgarian_parliament(year_path=current_year_p,
                                               year=year,
                                               source_html_path=source_file_p)
                elif country == 'united_kingdom':
                    parse_uk_parliament(year_path=current_year_p,
                                        year=year,
                                        source_html_path=source_file_p)
                elif country == 'ep':
                    parse_ep_parliament(year_path=current_year_p,
                                        year=year,
                                        source_xml_path=source_file_p,
                                        )
                elif country == 'cyprus':
                    # source_file_p = source_file_p.parent.joinpath("2017-03-24_ΙΑ΄ ΒΟΥΛΕΥΤΙΚΗ ΠΕΡΙΟΔΟΣ_ΣΎΝΟΔΟΣ Α΄_24.txt")
                    parse_cypriot_parliament(year_path=current_year_p,
                                             year=year,
                                             source_txt_path=source_file_p,
                                             )
                elif country == 'sweeden':
                    parse_swedish_parliament(year_path=current_year_p,
                                             year=year,
                                             source_html_path=source_file_p)
                elif country == 'greece':
                    parse_greek_parliament(year_path=current_year_p,
                                           year=year,
                                           source_doc_path=source_file_p
                                           )
                elif country == 'finland':
                    parse_finnish_parliament(year_path=current_year_p,
                                             year=year,
                                             source_pdf_path=source_file_p)
                elif country == 'malta':
                    parse_maltese_parliament(year_path=current_year_p,
                                             year=year,
                                             source_doc_path=source_file_p)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("country", type=str,
                        help="name of the national folder that should be parsed", metavar="path")
    parser.add_argument("--year", type=int, help="year to parse")
    args = parser.parse_args()
    input_path = args.country
    year = args.year

    main(country=input_path,
         year=year)
