# -*- coding: utf-8 -*-

### Code based on chozelinek/europarl

import pathlib
import numpy as np
import os
from glob import glob
import pathlib
import argparse
from lxml import etree, html
from lxml.html.clean import Cleaner
import fnmatch  # To match files by pattern
import regex as re  # Maybe not necessary
import time
import dateparser
import json


def timeit(method):
    """Time methods."""

    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print('%r %2.2f sec' %
              (method.__name__, te - ts))
        return result

    return timed


class TransformHtmlProceedingsToXml(object):
    """Get proceedings of the European Parliament."""

    @timeit
    def __init__(self,
                 indir=None,
                 outdir=None,
                 language=None,
                 pattern='*.html',
                 ):
        self.indir = indir
        self.outdir = outdir
        self.language = language
        self.pattern = pattern
        self.infiles = self.get_files(self.indir, self.pattern)
        self.n_proceedings = 0
        self.ns = {'re': 'http://exslt.org/regular-expressions'}
        self.loc_all = self.get_all_localized_vars()
        self.test_written_re = "|".join([value["in_writing"] for value in self.loc_all.values()])
        self.explanations_of_vote = re.compile(r' *EXPLANATIONS? OF VOTES?')
        self.langs = [
            "BG",
            "ES",
            "CS",
            "DA",
            "DE",
            "ET",
            "EL",
            "EN",
            "FR",
            "GA",
            "HR",
            "IT",
            "LV",
            "LT",
            "HU",
            "MT",
            "NL",
            "PL",
            "PT",
            "RO",
            "SK",
            "SL",
            "FI",
            "SV",
        ]
        self.main()

    def __str__(self):
        message = "{} EuroParl's {} proceedings transformed!".format(
            str(self.n_proceedings),
            self.language)
        return message

    def get_files(self, directory, fileclue):
        """Get all files in a directory matching a pattern.
        Keyword arguments:
        directory -- a string for the input folder path
        fileclue -- a string as glob pattern
        """
        matches = []
        for root, dirnames, filenames in os.walk(directory):
            if bool(filenames):
                for filename in fnmatch.filter(filenames, fileclue):
                    matches.append(os.path.join(root, filename))
        return matches

    def get_localized_vars(self):
        fname = self.language + ".json"
        fpath = os.path.join('localization', fname)
        with open(fpath, mode="r", encoding="utf-8") as jfile:
            content = jfile.read()
        vars = json.loads(content)
        return vars

    def get_all_localized_vars(self):
        locdir = os.path.join('localization')
        lang_vars = {}
        for root, dirnames, fpaths in os.walk(locdir):
            for fpath in fpaths:
                with open(str(os.path.join(root, fpath)), mode="r", encoding="utf-8") as jfile:
                    content = jfile.read()
                vars = json.loads(content)
                lang = fpath.split(".")[0]
                lang_vars[lang] = vars
        return lang_vars

    def read_html(self, infile):
        """Parse a HTML file."""
        with open(infile, encoding='utf-8', mode='r') as input:
            data = input.read()
            data = data.replace(u'\xa0', u' ')
            return html.document_fromstring(data)

    def regextract(self, content, a_pattern, target_dic, dic_attrib):
        """Extract information with a regular expression.
        Keyword arguments:
        a_string -- string
        a_regex -- a string
        target_dic -- a dictionary where the extraction has to be stored
        dic_attrib -- dictionary key where to store extraction
        """
        # match the a_regex in a_string
        is_match = re.match(r'{}'.format(a_pattern), content)
        # if match
        if is_match is not None:
            if dic_attrib not in target_dic.keys():
                target_dic[dic_attrib] = is_match.group(1)
                content = re.sub(r'{}'.format(a_pattern), r'', content)
        return content, target_dic

    def get_speaker_name(self, intervention):
        speaker_name = intervention.xpath(
            './/span[@class="doc_subtitle_level1_bis"]//text()')
        speaker_name = ''.join(speaker_name)
        speaker_name = re.sub(r'\n', r'', speaker_name)
        speaker_name = re.sub(r'\&amp;', r'&', speaker_name)
        speaker_name = re.sub(r'\([\p{Lu}\&/\-–\s]+\)', r'', speaker_name)
        speaker_name = re.sub(r'\(\p{Lu}\p{Ll}+[/-]ALE\)', r'', speaker_name)
        speaker_name = re.sub(r' +', r' ', speaker_name)
        speaker_name = re.sub(r'\A[\xad\s\.—–\-−,\)]+', r'', speaker_name)
        speaker_name = re.sub(
            r'([ \.]\p{LU}\.)[\xad\s\.—–\-−,:]+\Z',
            r'\1',
            speaker_name)
        speaker_name = re.sub(
            r'(\p{L}\p{L})[\xad\s\.—–\-−,\):]+\Z',
            r'\1',
            speaker_name)
        speaker_name = re.sub(r'(\p{L}\p{L}) . —\Z', r'\1', speaker_name)
        speaker_name = re.sub(
            r'(Figel’)[\xad\s\.—–\-−,\):]+\Z',
            r'\1',
            speaker_name)
        speaker_name = re.sub(r' \.\Z', r'', speaker_name)
        speaker_name = re.sub(r'\([\p{Lu}/\xad\-–]+\Z', r'', speaker_name)
        speaker_name = re.sub(r' +\Z', r'', speaker_name)
        speaker_name = re.sub(r', +,', r',', speaker_name)
        speaker_name = re.sub(r' +, +', r',', speaker_name)
        speaker_name = re.sub(r',+', r',', speaker_name)
        speaker_name = re.sub(r' *,(\S)', r', \1', speaker_name)
        speaker_name = re.sub(r',\Z', r'', speaker_name)
        speaker_name = re.sub(r'(Bartholomeos I)\.', r'\1', speaker_name)
        speaker_name = re.sub(
            r', im Namen der Delegation der britischen Konservativen',
            r'',
            speaker_name)
        return speaker_name

    def get_speaker_id(self, intervention):
        speaker_id = intervention.xpath('.//img[@alt="MPphoto"]')
        speaker_id = speaker_id[0].attrib['src']
        speaker_id = os.path.split(speaker_id)[1]
        speaker_id = os.path.splitext(speaker_id)[0]
        return speaker_id

    def get_is_mep(self, speaker_id):
        if speaker_id != 'photo_generic':
            output = True
        else:
            output = False
        return output

    def get_mode(self, intervention):
        in_writing = intervention.xpath(
            './/span[@class="italic"][text()[re:test(.,"{}")]]'.format(
                self.test_written_re),
            namespaces=self.ns)

        if len(in_writing) > 0:
            output = 'written'
            for writing in in_writing:
                writing.drop_tree()
        else:
            output = 'spoken'
        return output

    def get_role(self, intervention):
        roles = intervention.xpath(
            './/span[@class="italic"][text()[re:test(.,"^[\s\xad\-–−—\.]*(?:{})[\s\xad\-–−\.]*(?:\([A-Z][A-Z]\))?[\s\xad\-–−—\.]*$", "m")]]'.format(
                '|'.join(self.loc['roles'])), namespaces=self.ns)
        if len(roles) > 0:
            output = []
            for role in roles:
                if type(role) is str:
                    output.append(role)
                elif type(role) is html.HtmlElement:
                    output.append(role.text)
            for role in roles:
                lang = re.match(
                    r'.*({}).*'.format('|'.join(self.langs)),
                    role.text)
                if lang is not None:
                    i_lang = lang.group(1)
                else:
                    i_lang = None
                role.drop_tree()
        else:
            output = None
            i_lang = None
        if output is not None:
            output = " ".join(output)
            output = re.sub(r'\n', r' ', output)
            output = re.sub(r' +', r' ', output)
            output = re.sub(r'\([\p{Lu}\&/\-–]+\)', r'', output)
            output = re.sub(r'(\p{Ll})[\s\.\xad–\-−—,\)]+\Z', r'\1', output)
            output = re.sub(r'\A[\xad\s\.—–\-−,\)\(]+', r'', output)
            output = re.sub(r'[\xad\s\.—–\-−,\)]+\Z', r'', output)
        return output, i_lang

    def get_heading(self, section):
        heading = section.xpath('.//td[@class="doc_title"]//text()')
        heading = ''.join(heading)
        heading = heading.strip()
        heading = re.sub(r'\(\n', r'(', heading)
        heading = re.sub(r'\n,', r',', heading)
        return heading

    def get_language(self, s_intervention, p, i_lang, new_paragraphs):
        # Language is no longer part of the document, it always defaults to the requested lanugage
        language = p.xpath(
            './/span[@class="italic"][text()[re:test(.,"^[\xad\s\.—–\-−,\(]*({})[\xad\s\.—–\-−,\)]*")]]'.format(
                '|'.join(self.langs)), namespaces=self.ns)
        if len(language) > 0 and not self.explanations_of_vote.match(language[0].text):
            lang = re.match(
                r'.*({}).*'.format('|'.join(self.langs)),
                language[0].text)
            output = lang.group(1)
            for l in language:
                l.drop_tree()
        else:
            p = html.tostring(p, with_tail=True, encoding='utf-8').decode('utf-8')
            lang_in_text = re.search(
                r'\(({})\)'.format('|'.join(self.langs)),
                p)
            if lang_in_text is not None:
                output = lang_in_text.group(1)
                p = re.sub(r'\(({})\) *'.format('|'.join(self.langs)), r'', p)
            else:
                if len(new_paragraphs) == 0:
                    if 'role' in s_intervention.keys():
                        president_pattern = '|'.join(self.loc['president'])
                        if re.match(r'{}\Z'.format(president_pattern), s_intervention['role']):
                            output = 'unknown'
                        else:
                            if i_lang is None:
                                output = self.language.upper()
                            else:
                                output = i_lang
                    else:
                        if i_lang is None:
                            output = self.language.upper()
                        else:
                            output = i_lang
                else:
                    output = new_paragraphs[-1]['language']
            p = html.fromstring(p)
        return output, p

    def clean_paragraph(self, p):
        cleaner = Cleaner(remove_tags=['a'], kill_tags=['sup', 'img'])
        p = cleaner.clean_html(p)
        doc_subtitle = p.xpath('.//span[@class="doc_subtitle_level1_bis"]')
        for d in doc_subtitle:
            d.drop_tree()
        return p

    def get_paragraphs(self, intervention, s_intervention, i_lang=None):
        # Get rid of the italic information at the beginning
        additional_informations = intervention.xpath('.//span[@class="italic"]')
        for additional_information in additional_informations:
            additional_information.drop_tree()
        paragraphs = intervention.xpath(
            './/p[@class="contents" or @class="doc_subtitle_level1"]')
        new_paragraphs = []
        for p in paragraphs:
            new_p = {}
            p = html.tostring(
                p,
                with_tail=True,
                encoding='utf-8').decode('utf-8')
            p = re.sub(r'\n+', r' ', p)
            p = re.sub(r'<br ?/?>', r' ', p)
            p = html.fromstring(p)
            p = self.clean_paragraph(p)
            if i_lang:
                new_p['language'], p = self.get_language(
                    s_intervention,
                    p,
                    i_lang,
                    new_paragraphs)
            else:
                # Default to space
                new_p['language'] = ' '
            content = p.text_content()
            content = content.strip()
            content = re.sub(r'\t', r' ', content)
            content = re.sub(r'\xad', r'-', content)  # revise
            content = re.sub(r'\xa0', r' ', content)
            content = re.sub(r' +', r' ', content)
            content = re.sub(r'\. \. \.', r'...', content)
            content = re.sub(r'\.{3,}', r'…', content)
            content = re.sub(r'…\.\.', r'…', content)
            content = re.sub(r'^([\s\.—–\-−,\)]+)', r'', content)
            content = re.sub(r'([^\.])(…)', r'\1 \2', content)
            content = re.sub(r'\.…', r' …', content)
            content = re.sub(r'\( ?… ?\)', r'(…)', content)
            content = re.sub(r'(…)(\.)(\w)', r'\1\2 \3', content)
            content = re.sub(r'([\w”])(…)', r'\1 \2', content)
            content = re.sub(r'(…)(\w)', r'\1 \2', content)
            content = re.sub(r'\( +\)', r'', content)
            content = re.sub(r'\( +?', r'(', content)
            content = re.sub(r' +\)', r')', content)
            content = re.sub(r'(\[lt\]|<) ?BRK ?(\[gt\]|>)?', r'', content)
            content = re.sub(r'>(.+?)=', r'"\1"', content)
            content = re.sub(r's= ', r"s' ", content)
            content = re.sub(r'<Titre>', r'Titre', content)
            content = re.sub(r'<0', r'', content)
            content = re.sub(r'>', r'', content)
            content = re.sub(r'<', r'', content)
            content = re.sub(r'^,? *Neil,? +\. +– +', r'', content)
            content = re.sub(r'^\(PPE-DE\), +\. +– +', r'', content)
            content = re.sub(r'^\(Verts/ALE\), +\. +– +', r'', content)
            content = re.sub(r'\A\([\p{Lu}\&/\-–]+\)', r'', content)
            content = re.sub(r' +', r' ', content)
            content = re.sub(r'\A([\s\.—–\-−,\)]+)', r'', content)
            content = re.sub(r'^\((Madam President)', r'\1', content)
            content = re.sub(r'^\((Mr President)', r'\1', content)
            # for pattern in self.loc['more_roles']:
            #     content, s_intervention = self.regextract(
            #         content,
            #         pattern,
            #         s_intervention,
            #         'role')
            content = re.sub(r'\*{3,}', r'', content)
            new_p['content'] = content
            new_paragraphs.append(new_p)
        s_intervention['contents'] = new_paragraphs
        return s_intervention

    def add_root_attributes(self, root, tree, infile):
        root.attrib['id'] = os.path.splitext(os.path.basename(infile))[0]
        root.attrib['lang'] = self.language.lower()
        date_string = re.match(
            r'^(.+?,? \d.+?) - (.+)$',
            tree.xpath('//td[@class="doc_title" and @align="left" and @valign="top"]')[0].text)
        date = dateparser.parse(date_string.group(1)).date()
        place = date_string.group(2)
        root.attrib['date'] = str(date)
        root.attrib['place'] = place
        root.attrib['edition'] = tree.xpath('//td[@class="doc_title" and @align="right" and @valign="top"]')[0].text
        pass

    def intervention_to_xml(self, x_section, s_intervention):
        x_intervention = etree.SubElement(x_section, 'intervention')
        if 'id' in s_intervention.keys():
            x_intervention.attrib['id'] = s_intervention['id']
        if 'speaker_id' in s_intervention.keys():
            x_intervention.attrib['speaker_id'] = s_intervention['speaker_id']
        if 'name' in s_intervention.keys():
            x_intervention.attrib['name'] = s_intervention['name']
        if 'is_mep' in s_intervention.keys():
            x_intervention.attrib['is_mep'] = str(s_intervention['is_mep'])
        if 'mode' in s_intervention.keys():
            x_intervention.attrib['mode'] = s_intervention['mode']
        if 'role' in s_intervention.keys():
            x_intervention.attrib['role'] = s_intervention['role']
        for paragraph in s_intervention['contents']:
            if len(paragraph['content']) > 0:
                if not re.match(r'^\(.+?\)$', paragraph['content']):
                    x_p = etree.SubElement(
                        x_intervention,
                        'p',
                        sl=paragraph['language'].lower())
                    x_p.text = paragraph['content']
                else:
                    etree.SubElement(
                        x_intervention,
                        'a',
                        text=paragraph['content'])
        pass

    def serialize(self, infile, root):
        ofile_name = os.path.splitext(os.path.basename(infile))[0]
        ofile_path = os.path.join(self.outdir, ofile_name + '.xml')
        xml = etree.tostring(
            root,
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True).decode('utf-8')
        with open(ofile_path, mode='w', encoding='utf-8') as ofile:
            ofile.write(xml)
        pass

    def get_element_id(self, element):
        output = element.getprevious().attrib['name']
        return output

    def main(self):
        for infile in self.infiles:
            print(infile)
            tree = self.read_html(infile)
            root = etree.Element('text')
            self.add_root_attributes(root, tree, infile)
            sections = tree.xpath(
                '//table[@class="doc_box_header" and @cellpadding="0"]')
            for section in sections:
                heading = self.get_heading(section)
                section_id = self.get_element_id(section)
                x_section = etree.SubElement(root, 'section')
                x_section.attrib['id'] = section_id
                x_section.attrib['title'] = heading
                interventions = section.xpath(
                    './/table[@cellpadding="5"][.//img[@alt="MPphoto"]]')
                for idx, intervention in enumerate(interventions):
                    s_intervention = {}
                    intervention_id = self.get_element_id(intervention)
                    s_intervention['id'] = intervention_id
                    # i_lang = None
                    s_intervention['speaker_id'] = self.get_speaker_id(intervention)
                    s_intervention['is_mep'] = self.get_is_mep(
                        s_intervention['speaker_id'])
                    s_intervention['mode'] = self.get_mode(intervention)
                    speaker_name = self.get_speaker_name(intervention)
                    # president_pattern = '|'.join(self.loc['president'])
                    # if re.match(r'{}\Z'.format(president_pattern), speaker_name):
                    #     s_intervention['role'] = speaker_name
                    # else:
                    #     s_intervention['name'] = speaker_name
                    s_intervention['name'] = speaker_name
                    # role, i_lang = self.get_role(intervention)
                    # if role is not None:
                    #     s_intervention['role'] = role
                    s_intervention = self.get_paragraphs(
                        intervention,
                        s_intervention,
                    )
                    self.intervention_to_xml(x_section, s_intervention)
            self.serialize(infile, root)
            self.n_proceedings += 1
        pass


def main():
    root_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'ep')
    years = list(np.arange(2009, 2022))

    for year in years:
        year_path = root_path.joinpath(str(year), 'source')
        TransformHtmlProceedingsToXml(indir=year_path,
                                      outdir=year_path,
                                      language='en',
                                      )


if __name__ == "__main__":
    main()