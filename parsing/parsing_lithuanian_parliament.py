import re
import pathlib
from scrapy.http import HtmlResponse
import datetime
from eia_crawling.spiders.utils import write_csv, normalize_string

MONTHS = {"sausio": 1,
          "vasario": 2,
          "kovo": 3,
          "balandžio": 4,
          "gegužės": 5,
          "birželio": 6,
          "liepos": 7,
          "rugpjūčio": 8,
          "rugsėjo": 9,
          "spalio": 10,
          "lapkričio": 11,
          "gruodžio": 12}


def parse_lithuanian_parliament(year_path: pathlib.Path,
                                year: int,
                                source_html_path: pathlib.Path):
    # Get file name
    source_html_path = source_html_path
    file_name = source_html_path.stem

    # Read source html
    source_f = open(source_html_path, "rb")
    source_html = source_f.read()
    response = HtmlResponse(url="", body=source_html)

    # Get the date of the session (many possible formats)
    date_list = response.xpath('//p[@class="Topic"]//text()').getall()
    if not date_list:
        # Try this option to get the date
        date_list = response.xpath(
            '//p[@class="MsoTitle" and contains(span/text(), "STENOGRAMA")]//following::p[@class="MsoNormal"][1]//text()').getall()
    if not date_list:
        # Try this option
        date_list = response.xpath(
            '//p[(@class="MsoNormal" or @class="Roman") and contains(b/span/text(), "Nr.")][1]/following::*[1]//text()').getall()
    if not date_list:
        # Try this option
        date_list = response.xpath('//h3[contains(span/text(), "Nr.")][1]/following::*[1]//text()').getall()
    if not date_list:
        # Try this option
        date_list = response.xpath('//h6[contains(span/text(), "Nr.")][1]/following::*[1]//text()').getall()
    if not date_list:
        # Try this option
        date_list = response.xpath('//h4[contains(span/text(), "Nr.")][1]/following::*[1]//text()').getall()
    date = " ".join(date_list)
    if date:
        date = re.sub(r'm\s*\.|d\.', '', date)
        date = normalize_string(date)
        date = re.sub(r'\s+', ' ', date)
        # Split again to safely replace month and join (setting lithuanian locale didn´t work)
        date_list = date.split()
        try:
            date_list[1] = str(MONTHS[date_list[1]])
        except:
            raise AssertionError
        date = " ".join(date_list)
        # Parse the date into date time in local time
        date = datetime.datetime.strptime(date, '%Y %m %d').isoformat()
    else:
        raise AssertionError

    # Get the sitting
    try:
        sitting = re.search(r'(?<=Nr\.\s)\d{1,3}', file_name).group()
    except:
        raise AssertionError

    # Define parliament and iso3country
    parliament = "LT-Seimas"
    iso3country = "LTU"
    term = "6"

    parsed_output = []

    i = 0
    j = 0

    current_pirmininke = None
    current_pirmininkas = None
    current_pirmininke_party = ''
    current_pirmininkas_party = ''

    # Identify the speech paragraphs (incl. speakers)
    paragraphs_raw = response.xpath(
        '//p[(@class="Roman"  and i) or @class="Pertrauka"][1]/following::p[(@class="Roman" or @class="MsoNormal" or @class="MsoBodyTextIndent")and self::*[span] and following::div[@id="ftn1"]]')
    for paragraph_raw in paragraphs_raw:

        # Get the paragraph text
        text_raw_list = paragraph_raw.xpath('./span//text()[not(parent::i)]').getall()
        text_raw = " ".join(text_raw_list)
        text_raw = re.sub(r'\n', ' ', text_raw)
        text_raw = text_raw.replace('\u00ad', '')
        text = re.sub(r'\(.*?\)', '', text_raw)
        text = normalize_string(text)
        # Skip empty paragraphs
        if text == "":
            continue

        # Get the speaker and the party for the corresponding paragraph
        # Check whether the raw paragraph contains a bold-tag ==> In this case it is the beginning of a new speech
        if paragraph_raw.xpath('./b'):
            # Check whether we really found a proper speaker
            speaker_raw_list = paragraph_raw.xpath('.//b//text()').getall()
            speaker_raw = " ".join(speaker_raw_list)
            speaker_raw = normalize_string(speaker_raw)
            # Remove the "." at the end of the speaker name
            speaker = speaker_raw.rstrip(".")
            speaker = speaker.replace('\u00ad', '')

            # Really found a new speaker (small letters indicate that it might not be a real speaker)
            if re.search(r'[a-z]', speaker):
                if re.search(r'\(?\s*.\.\s*.*?\)?', speaker):
                    is_real_speaker = True
                    speaker = re.sub(r'[a-z]', '', speaker)
                    speaker = speaker.rstrip(". ")
                else:
                    is_real_speaker = False
            else:
                is_real_speaker = True

            if is_real_speaker:
                # Beginning of new speech
                i += 1
                j = 1

                # Treat the president differently
                if ("PIRMININKĖ" in speaker or "PIRMININKAS" in speaker) and re.search(r'\(?\s*.\.\s*.*?\)?', speaker):
                    # Try to find the speaker name in brackets
                    speaker_start_i = re.search(r'\(?\s*.\.\s*.*?\)?', speaker).start()
                    speakerrole = speaker[:speaker_start_i]
                    speakerrole = speakerrole.strip()
                    speaker = speaker[speaker_start_i:]
                    speaker = speaker.strip("() .")
                    if "PIRMININKĖ" in speakerrole:
                        current_pirmininke = speaker
                    elif "PIRMININKAS" in speakerrole:
                        current_pirmininkas = speaker
                elif "PIRMININKĖ" in speaker and current_pirmininke:
                    speakerrole = "PIRMININKĖ"
                    speaker = current_pirmininke
                elif "PIRMININKAS" in speaker and current_pirmininkas:
                    speakerrole = "PIRMININKAS"
                    speaker = current_pirmininkas
                elif "PIRMININKĖ" in speaker:
                    speakerrole = "PIRMININKĖ"
                    speaker = ''
                elif "PIRMININKAS" in speaker:
                    speakerrole = "PIRMININKAS"
                    speaker = ''
                else:
                    speakerrole = ''

                # Get the party
                party_raw_list = paragraph_raw.xpath('(.//i)[1]//text()').getall()
                party_raw = " ".join(party_raw_list)
                # Parties do not contain lowercase letters (except for one party)
                if party_raw and not re.search(r'[a-z]|LiCSF|J(LiCS\s*ir\s*TPP)F', party_raw):
                    party_raw = party_raw.replace('\u00ad', '')
                    party = normalize_string(party_raw)
                    if party == 'L':
                        # Quick fix for strange html format for this party
                        party = 'LiCSF'
                    elif party == 'J':
                        party = 'J(LiCS ir TPP)F'

                    # Set the current party for the presidents
                    if speakerrole == "PIRMININKĖ":
                        current_pirmininke_party = party
                    elif speakerrole == "PIRMININKAS":
                        current_pirmininkas_party = party
                else:
                    # Check whether we have stored a party for the presidents
                    if speakerrole == "PIRMININKĖ":
                        party = current_pirmininke_party
                    elif speakerrole == "PIRMININKAS":
                        party = current_pirmininkas_party
                    else:
                        party = ''
            else:
                # The speech started earlier so just take the previous speaker and party
                j += 1

                try:
                    speaker = parsed_output[-1].get("speaker")
                    speakerrole = parsed_output[-1].get("speakerrole")
                    party = parsed_output[-1].get("party")
                except:
                    # There must be a speaker
                    raise AssertionError

        else:
            # The speech started earlier so just take the previous speaker and party
            j += 1

            try:
                speaker = parsed_output[-1].get("speaker")
                speakerrole = parsed_output[-1].get("speakerrole")
                party = parsed_output[-1].get("party")
            except:
                # There must be a speaker
                raise AssertionError

        # Find the preceding agenda point
        if paragraph_raw.xpath('./preceding::p[@class="Roman12"]'):
            agenda_title_raw_list = paragraph_raw.xpath('./preceding::p[@class="Roman12"][1]//text()').getall()
            agenda_title_raw = " ".join(agenda_title_raw_list)
            agenda_title_raw = re.sub(r'\n', ' ', agenda_title_raw)
            agenda_title_raw = agenda_title_raw.replace('\u00ad', '')
            agenda_title = normalize_string(agenda_title_raw)
        else:
            agenda_title = ''

        parsed_output.append(
            {'date': date[:10],
             'term': term,
             'sitting': sitting,
             'agenda': agenda_title,
             'speechnumber': i,
             'paragraphnumber': j,
             'speaker': speaker,
             'speakerrole': speakerrole,
             'party': party,
             'text': text,
             'parliament': parliament,
             'iso3country': iso3country
             })

    # Write parsed data
    path = year_path.joinpath(f"{file_name}_parsed.csv")
    write_csv(path, data=parsed_output,
              fieldnames=['date', 'term', 'sitting', 'agenda', 'speechnumber', 'paragraphnumber', 'speaker', 'speakerrole', 'party', 'text', 'parliament', 'iso3country'])
