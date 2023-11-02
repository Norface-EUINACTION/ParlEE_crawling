import pathlib
import sys
from bs4 import BeautifulSoup
import re
from dateutil import parser
import json
from eia_crawling.spiders.utils import normalize_string

sys.path.append('../')

ENCODING = 'utf8'


def parse_eu_final_act_full(doc_path: pathlib,
                            doc_name: str):
    """
    Function parsing Articles alongside their numbers from a single .html document

    :param doc_path:        path to the folder containing document
    :param doc_name:        name of the document

    :returns list of dicts with following keys: 'celex', 'year', 'title', 'art_no', 'text'
    """

    def get_title(soup_object: BeautifulSoup):
        """
        Get the title of document (e.g. directive, regulation or decision, but list NOT exhaustive)
        """
        try:
            root = soup_object.find('p', {'class': re.compile('oj-doc-ti|doc-ti')})
            # Case 1: Titles lies inside the tag
            title = root.text.split()[0]
            # Case 2: Titles lies inside the sub-tag
            first_child = root.findChild()
            if first_child is not None:
                title = first_child.text
            return title

        except AttributeError:
            print('Title tag not found')

    def get_year(soup_object: BeautifulSoup):
        """
        Get the year of document as int (from the content, NOT from the path)
        """
        try:
            root = soup_object.find('p')
            year = root.text
            year = parser.parse(year).year
            return year
        except AttributeError:
            print('Year tag not found')

    def if_correlation_table(soup_object: BeautifulSoup):
        """
        Check whether document contains Correlation Table
        """

        if len(soup.findAll(text=re.compile('CORRELATION\s+TABLE'))) == 0:
            return False
        else:
            return True

    def get_text(soup_object: BeautifulSoup):
        """
        Iterates over Articles in the document retrieving Article number and respective text.
        Handles two cases caused by differences in HTML structure across files
        """

        # Get a first tag (tag with text 'Article 1')
        pattern = re.compile(r'^\s*Article\s*1$')
        first_tag = soup_object.find(text=pattern).parent
        # Get a parent of starting tag to navigate to other tags
        parent_tag = first_tag.parent

        # List of tuples to be filled with text and Article number for each Article in BS object
        text_list = []

        # Handle two edge-cases:
        # Case 1: Articles lie in direct children nodes of tag <body>
        if parent_tag.name == 'body':
            # Get all tags that start an Article (all starting tags)
            starting_tags = soup_object.body.findChildren('p', {'class': re.compile(r'^(oj-ti-art)|^(ti-art)')},
                                                          recursive=False)
            # Retrieve tags belonging to an Article starting form starting_tag

            for tag in starting_tags:  # todo: improve readabality
                art_no = re.findall(r'\d+', tag.text)[0]
                article_content = []  # contains all the tags for one article
                current_tag = tag

                while current_tag.find_next_sibling() is not None:
                    has_class = current_tag.find_next_sibling().attrs.__contains__('class')

                    if not has_class or (
                            has_class and current_tag.find_next_sibling()['class'][0] not in ['ti-art', 'oj-ti-art',
                                                                                              'final']):
                        current_tag = current_tag.find_next_sibling()
                        article_content.append(current_tag)
                    else:
                        break

                # Retrieve text from tags belonging to one Article
                text = ' '.join([normalize_string(t.text) for t in article_content])
                # Append retrieved text to a list containing texts from all Articles found in BS object
                text_list.append((art_no, text))

        # Case 2: Articles are nested in 'div' tags, each of them having its own 'div' tag
        elif parent_tag.name == 'div':
            pattern_div = re.compile(r'^\d+')
            first_div = parent_tag
            all_divs = [first_div] + first_div.find_next_siblings('div', {'id': pattern_div})

            # Retrieve text from tags belonging to one Article
            for tag in all_divs:
                art_no = re.findall(r'\d+', tag['id'])[0].lstrip("0")
                text_nodes = tag.findAll(text=True)
                text = ' '.join([normalize_string(t) for t in
                                 text_nodes[2:]])  # Omit title tag (e.g. 'Article 10' should not appear in text entry)
                # Append retrieved text to a list containing texts from all Articles found in BS object
                text_list.append((art_no, text))

        return text_list

    ### Actual parsing using helper functions from above ###
    output = []
    # Access file to be parsed
    target_path = doc_path.joinpath(doc_name + '.html')

    # Get CELEX number
    json_path = target_path.parent.joinpath(target_path.stem + '.json')
    with open(str(json_path)) as file:
        json_meta_data = json.load(file)
        doc_celex = list(json_meta_data.values())[0]['celex']

    # Convert .html to Beautiful Soup object
    soup = BeautifulSoup(open(str(target_path), encoding=ENCODING), "html.parser")

    # Get required features
    doc_year = get_year(soup)  # get year
    doc_title = get_title(soup)  # get title
    doc_text_attrs = get_text(soup)  # get Articles

    # Check for correlation table
    has_correlation_table = if_correlation_table(soup)

    # Append each Article and other features to list of dictionaries
    for t in doc_text_attrs:
        # Normalize text
        parsed_text = normalize_string(t[1])
        parsed_art_no = t[0]
        output.append(
            {'celex': doc_celex, 'year': doc_year, 'title': doc_title, 'art_no': parsed_art_no, 'text': parsed_text,
             'has_correlation_table': has_correlation_table})

    # Check the order, if not preserved, merge dictionaries
    k = 1
    to_remove = []
    for art in output[1:]:
        if int(art['art_no']) == k + 1:
            k += 1
        else:
            output[k - 1]['text'] = ' '.join([output[k - 1]['text'], art['text']])
            to_remove.append(art)

    for el in to_remove:
        output.remove(el)  # check for uniqueness

    return output

# What to have in mind in future parsing tasks:
# (1) MemoryError likely to occur if all docs parsed at once!
# (2) Check .utils, many useful functions already implemented
# (3) For tags using list comprehension improves readability
