import pathlib
from bs4 import BeautifulSoup
import re
import json
from eia_crawling.spiders.utils import normalize_string
import datetime

ENCODING = 'utf8'
OPENING_PHRASE = re.compile(
    r'.*((HAS|HAVE)\s*ADOPTED|(HAS|HAVE)\s*DECIDED|HAS\s*HAVE\s*ADOPTED)|HAS\s*Ö\s*HAVE\s*Õ\s*ADOPTED.*')
CLOSING_PHRASE = re.compile(r'Done\s+at')


### Case 1: Not formatted HTML ###
def parse_eu_proposal_not_formatted(doc_path: pathlib,
                                    doc_name: str):
    def assign_text_to_art(tag):
        speech = ''
        if_end = None
        if tag.get_text() == 'Sole Article':
            art_no = 1
        else:
            art_no = re.findall(r'\d+', tag.get_text())[0]  # number of Article
            art_no = int(art_no)

        while tag.find_next_sibling() is not None:
            next_text = tag.find_next_sibling().get_text()
            next_article_regex = re.compile(r'^\s*Article\s*' + re.escape(str(art_no + 1)))

            if bool(re.match(CLOSING_PHRASE, next_text)):
                if_end = True
                break

            if bool(re.match(next_article_regex, next_text)):
                if_end = False
                break

            speech = ' '.join([speech, next_text])
            tag = tag.find_next_sibling()

        return speech, if_end

    def get_celex(path: pathlib):
        # Get CELEX number
        target_path = path.joinpath(doc_name + '.html')
        json_path = target_path.parent.joinpath(target_path.stem + '.json')
        with open(str(json_path)) as file:
            json_meta_data = json.load(file)
            doc_celex = list(json_meta_data.values())[0]['celex']

        return doc_celex

    # Access file to be parsed
    target_path = doc_path.joinpath(doc_name + '.html')

    # Convert .html to Beautiful Soup object
    soup = BeautifulSoup(open(str(target_path), encoding=ENCODING), "html.parser")

    ## Find first tag
    opening_tag = soup.find('p', text=OPENING_PHRASE)
    first_tag_pattern = re.compile(r'^\s*Article\s*1.*|Sole Article')
    first_tag = opening_tag.find_next_sibling('p', text=first_tag_pattern)

    ## Get all potential siblings that start further Articles
    starting_pattern = re.compile(r'^\s*Article\s*\d{0,3}')
    starting_tags = first_tag.find_next_siblings('p', text=starting_pattern)

    ## Get text from first paragraph alongside boolean indicator whether it's the only Article in the doc
    art1, end = assign_text_to_art(first_tag)

    ## Initialize list of dictionaries
    articles = [{'celex': get_celex(doc_path), 'art_no': 1, 'text': normalize_string(art1.strip('\n'))}]

    ## Get text from siblings if order is preserved
    if not end:
        i = 1
        for s in starting_tags:
            try:
                try:
                    current_art_no = int(s.get_text().split()[1])
                except IndexError:
                    current_art_no = int(s.get_text().replace('Article', ''))
            except ValueError:
                current_art_no = 1000
            if current_art_no == i + 1:
                text, end = assign_text_to_art(s)
                articles.append({'celex': get_celex(doc_path), 'art_no': current_art_no, 'text': normalize_string(text.strip('\n'))})
                i += 1
                if end:
                    break

    return articles


### Case 2: Formatted HTML ###
def parse_eu_proposal_formatted(doc_path: pathlib,
                                doc_name: str):
    def get_celex(path: pathlib):
        # Get CELEX number
        target_path = path.joinpath(doc_name + '.html')
        json_path = target_path.parent.joinpath(target_path.stem + '.json')
        with open(str(json_path)) as file:
            json_meta_data = json.load(file)
            doc_celex = list(json_meta_data.values())[0]['celex']

        return doc_celex

    # Access file to be parsed
    target_path = doc_path.joinpath(doc_name + '.html')

    # Convert .html to Beautiful Soup object
    soup = BeautifulSoup(open(str(target_path), encoding=ENCODING), "html.parser")

    # Get all tags that start an Article
    art_tags = soup.findAll('p', attrs={'class': ['Titrearticle']})
    # List of tuples to be filled with text and Article number for each Article in BS object
    articles = []

    for art_tag in art_tags:
        # Filter out starting tags which do not start articles - handling structure inconsistency (e.g. 2012/0150(COD))
        if not bool(re.search(r'^\s+Article\s+\d+', art_tag.get_text())):
            pass
        else:
            first_tag = art_tag

            # Get Article number
            art_no = re.findall(r'\d+', first_tag.get_text())[0]

            if first_tag.find_next_sibling() is None:
                current_content_tag = first_tag.parent.find_next_sibling()
                current_tag = current_content_tag.findAll()[0]
            else:
                current_tag = first_tag.find_next_sibling()

            text = ''

            while current_tag.has_attr('class'):
                if (current_tag['class'][0] == "Titrearticle" and bool( # no need bool, empty string evaluates to False
                        re.search(r'Article\s+\d+', current_tag.get_text()))) or re.search(CLOSING_PHRASE,
                                                                                           current_tag.get_text()):
                    break
                else:
                    text = ' '.join([text, current_tag.get_text()])
                    # Text might be partitioned in two different parent tags (e.g. 2015/0225)
                    if current_tag.find_next_sibling() is None:
                        current_content_tag = current_tag.parent.find_next_sibling()
                        current_tag = current_content_tag.findAll()[0]
                    else:
                        current_tag = current_tag.find_next_sibling()

            articles.append(
                {'celex': get_celex(doc_path), 'art_no': art_no, 'text': normalize_string(text.strip('\n'))})
    # Check the order, if not preserved, merge dictionaries
    k = 1
    to_remove = []
    for art in articles[1:]:
        if int(art['art_no']) == k + 1:
            k += 1
        else:
            articles[k-1]['text'] = ' '.join([articles[k-1]['text'], art['text']])
            to_remove.append(art)

    for el in to_remove:
        articles.remove(el) # check for uniqueness

    return articles
