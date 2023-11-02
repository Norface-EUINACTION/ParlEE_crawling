import pathlib
import os
import re
from eia_crawling.spiders.utils import write_csv
import xml.etree.ElementTree as ET
from lxml.etree import parse, tostring
import locale
from datetime import datetime

ROOT = pathlib.Path(__file__).absolute().parent.parent
DATA_PATH = ROOT.joinpath("spiders", "data", "national", "italy")

PARSED_PATH = ROOT.joinpath("parsing", "italy")

# List variable for the political parties
POL_PARTIES = ["PD", "FI", "M5S", "LEU", "LEGA", "LSP", "FDI"]

# THIS PART IS FOR YEARS 2009,2010,2011,2012,2013,2014,2015,2016
for year in range(2015,2016):
    YEAR_PATH = DATA_PATH.joinpath(str(year), "source")

    # Create the parsed directory
    try:
        YEAR_PARSED_PATH = PARSED_PATH.joinpath(str(year))
        os.mkdir(YEAR_PARSED_PATH)
    except Exception as e:
        print(e)

    #for xmlfile in os.listdir(YEAR_PATH):
    for xmlfile in ["/Users/mertozlutiras/Desktop/MEGA/MERT/work/NLP/eia-crawling/eia_crawling/spiders/data/national/italy/2015/source/20150309_387_session.xml"]:
        if xmlfile.endswith("xml"):

            # Define these for start
            speech_no = 0
            parsed_text = []

            tree = parse(str(YEAR_PATH.joinpath(xmlfile)))
            root = tree.getroot()

            # Date Found and Converted to the Format we seek
            locale.setlocale(locale.LC_TIME, "it_IT")
            dateElement = root.find("./metadati/dataEstesa")
            date = dateElement.text
            date_elems = date.split(" ")

            # Patch solution for some date type errors
            if len(date_elems) > 4:
                date = " ".join(date_elems[:4])

            # Another patch solution for dates of type "venerdi 1° dicembre 2017"
            if date_elems[1][-1] == "°":
                date_elems[1] = date_elems[1][:-1]
                date = " ".join(date_elems)

            try:
                date_object = datetime.strptime(date, "%A %d %B %Y")
            except Exception as e:
                print(xmlfile)
                print(e)

            # date is here, prepared in the correct form
            DATE = date_object.strftime("%Y-%m-%d")

            # Find and preprocess agendas then append them to their list
            agendas = root.findall("./resoconto/dibattito")
            agenda_list = []


            for agenda in agendas:
                # Find the agenda and preprocess it
                text_agenda = agenda.xpath("./titolo//text()")
                text_agenda = text_agenda[0].replace('\n\xa0', ' ')
                text_agenda = text_agenda.replace('\xa0', ' ')

                # Each intervento is a person's speech
                interventos = agenda.findall("./intervento")
                for intervento in interventos:
                    try:
                        # In siglagruppo tag we have the party information
                        party = intervento.xpath("./@siglaGruppo")[0]
                    except:
                        party = ""
                    speech_no += 1
                    speeches =[]
                    try:
                        speaker = intervento.xpath("./nominativo//text()")[0]
                        testos = intervento.xpath("./testoXHTML")
                        for testo in testos:
                            speeches.append(testo.xpath(".//text()"))

                    except:
                        # This is a special case where in some xml files they put nominativo tag inside the testoXHTML
                        # We need to skip the first element of the speechgroup, because it's the speaker name
                        speaker = intervento.xpath("./testoXHTML/nominativo//text()")[0]
                        speeches.append(list(intervento.xpath("./testoXHTML//text()")))
                        # The first element of the speech is sometimes "\n\t\t\t\t\t..."
                        # The second element is the speaker name
                        # If 0th element is this meaningless element and 1st is speaker name, we start speeches from 2nd element
                        if re.match("^\\n.*", speeches[0][0]):
                            speeches[0] = speeches[0][2:]
                        # If 0th element is OK, then it is the speaker name, so we start speeches from 1st element
                        else:
                            speeches[0] = speeches[0][1:]

                    if year >= 2018:
                        if intervento.xpath("./interventoVirtuale//text()") != []:
                            for interventovirtuale in intervento.xpath("./interventoVirtuale"):
                                speeches.append(interventovirtuale.xpath(".//text()"))

                    # If the speech is cut with a br tag, the speechgroup has several elements
                    # as well, so I need to check inside too
                    for speechgroup in speeches:

                        for i in range(len(speechgroup)):
                            speech = speechgroup[i]
                            if i == len(speechgroup)-1:
                                break

                            try:
                                # Some cleaning
                                speech = speech.replace("\n"," ")
                                speech = speech.replace("\r", " ")
                                speech = re.sub(' +', ' ', speech)
                            except Exception as e:
                                print(e)

                            # If it ends with xa0, it will be a separate paragraph
                            if speech.endswith("\xa0"):
                                speech = speech.replace("\xa0", " ")
                                continue
                            else:
                                if i == len(speechgroup) - 1:
                                    break

                                    # Keep checking until the speech at index i doesn't end with \n\xa0

                                while not speech.endswith("\xa0"):
                                    # We have to update the element
                                    speechgroup[i] = speechgroup[i] + speechgroup[i + 1]
                                    speechgroup.pop(i + 1)
                                    if i == len(speechgroup)-1:
                                        break

                            if i == len(speechgroup) - 1:
                                break

                    for speechgroup in speeches:
                        # If the speechgroup is empty, simply remove it
                        if speechgroup == []:
                            speeches.remove(speechgroup)


                    # Paragraph no is set to 0 before going over them
                    paragraph_no = 0

                    try:
                        for speechgroup in speeches:
                            #Every paragraph is separated inside speechgroup as well
                            for speech in speechgroup:
                                paragraph_no += 1
                                text = speech
                                # If the text starts with ". ", we get rid of it
                                if re.match("\..*", text):
                                    text = text[2:]

                                # Let's check if the party is in the beginning of speech
                                try:

                                    party_check = re.match("\(w{2,5})", text).group(0)
                                    # let's make the text get rid of party_check
                                    text = text.replace(party_check, "")

                                    # Also get rid of paranthesis
                                    party_check = party_check[1:-1]
                                except:
                                    pass

                                try:
                                    if party_check in POL_PARTIES:
                                        party = party_check
                                    else:
                                        party = ""
                                except:
                                    party = ""

                                # Clean the starting blanks in beginning also other blanks
                                # If text starts with " " or " ." or multiple blanks are present
                                # We go into loop, and we change accordingly to the problem
                                while re.match("^ .*", text) or re.match("^\..*", text) or re.match(" +", text):
                                    if re.match("^ .*", text) or re.match("^\..*", text):
                                        text = text[1:]
                                    if re.match(" +", text):
                                        text = re.sub(' +', ' ', text)

                                text = text.replace("\n", "")
                                text = text.replace("\r", "")
                                text = text.replace("\t", "")
                                speaker = re.sub(' +', ' ', speaker)
                                speaker = speaker.replace("\n", "")
                                speaker = speaker.replace("\r", "")
                                speaker = speaker.replace("\t", "")

                                parsed_paragraph = {"date": DATE,
                                                    "agenda": text_agenda,
                                                    "speechnumber": speech_no,
                                                    "paragraphnumber": paragraph_no,
                                                    "speaker": speaker,
                                                    "party": party,
                                                    "text": text, #There is only one element in that list, that's why taking the first element
                                                    "parliament": "IT-Parlamento",
                                                    "iso3country": "ITA",
                                                    "partyname": "",
                                                    "speakerrole": "",
                                                    "period": "",
                                                    "parliamentary_session": "",
                                                    "sitting": "",
                                                    }
                                parsed_text.append(parsed_paragraph)

                    except Exception as e:
                        print(xmlfile)
                        print(e)

                    # Now only for year 2017, we will look at the subagendas and also add them to our csv
                    try:
                        #Fases are subagendas
                        fases = agenda.findall("./fase")
                        for fase in fases:
                            #Title of the subagenda concatanated with agenda
                            text_fase = fase.xpath("./titolo//text()")
                            text_fase = text_fase[0].replace('\n\xa0', ' ')
                            text_fase = text_fase.replace('\xa0', ' ')
                            text_agenda_w_fase = text_agenda + " " + text_fase

                            # Each intervento is a person's speech
                            fase_interventos = fase.findall("./intervento")

                            for fase_intervento in fase_interventos:

                                try:
                                    # In siglagruppo tag we have the party information
                                    party = fase_intervento.xpath("./@siglaGruppo")[0]
                                except Exception as e:
                                    party = ""

                                speech_no += 1
                                speeches = []
                                # In some cases, Speaker name is found inside testoXHTML as the first element of nominativo
                                try:
                                    speaker = fase_intervento.xpath("./testoXHTML/nominativo//text()")[0]

                                    # In this once, since the speaker name is inside testo, there can't be many testos
                                    # We don't need to check for testos
                                    # Let's add the text in testoxhtml inside fase as our speeches
                                    speeches.append(list(fase_intervento.xpath("./testoXHTML//text()")))


                                    # If 0th element is this meaningless element and 1st is speaker name, we start speeches from 2nd element
                                    if re.match("^\\n.*", speeches[0][0]):
                                        speeches[0] = speeches[0][2:]
                                    # If 0th element is OK, then it is the speaker name, so we start speeches from 1st element
                                    else:
                                        speeches[0] = speeches[0][1:]

                                # In others it's not inside the testoXHTML, and speeches are inside testoxhtml
                                except:
                                    speaker = fase_intervento.xpath("./nominativo//text()")[0]
                                    # We should check for different testos
                                    testos = fase_intervento.findall("./testoXHTML")
                                    for testo in testos:
                                        speeches.append(list(testo.xpath(".//text()")))


                                for speechgroup in speeches:

                                    for i in range(len(speechgroup)):
                                        speech = speechgroup[i]
                                        if i == len(speechgroup) - 1:
                                            break

                                        try:
                                            # Some cleaning
                                            speech = speech.replace("\n", " ")
                                            speech = speech.replace("\r", " ")
                                            speech = re.sub(' +', ' ', speech)
                                        except Exception as e:
                                            print(e)

                                        if speech.endswith("\xa0"):
                                            speech = speech.replace("\xa0", " ")
                                            continue

                                        else:
                                            if i == len(speechgroup) - 1:
                                                break

                                                # Keep checking until the speech at index i doesn't end with \n\xa0

                                            while not speech.endswith("\xa0"):
                                                speechgroup[i] = speechgroup[i] + speechgroup[i + 1]
                                                speechgroup.pop(i + 1)
                                                if i == len(speechgroup) - 1:
                                                    break

                                        if i == len(speechgroup) - 1:
                                            break

                                # Paragraph no is set to 0 before going over them
                                paragraph_no = 0
                                for speechgroup in speeches:
                                    paragraph_no += 1
                                    text = speechgroup[0]
                                    # If the text starts with ". ", we get rid of it
                                    if re.match("\..*", text):
                                        text = text[2:]

                                    # Let's check if the party is in the beginning of speech
                                    # We do this if we couldn't find the party yet
                                    if party == "":
                                        try:
                                            party_check = re.match("\(.*\)", text).group(0)
                                            # let's make the text get rid of party_check
                                            text = text.replace(party_check, "")

                                            # Also get rid of paranthesis
                                            party_check = party_check[1:-1]
                                        except:
                                            pass

                                        try:
                                            if party_check in POL_PARTIES:
                                                party = party_check
                                            else:
                                                party = ""
                                        except:
                                            party = ""

                                    # Clean the starting blanks in beginning also other blanks
                                    # If text starts with " " or " ." or multiple blanks are present
                                    # We go into loop, and we change accordingly to the problem
                                    while re.match(" .*", text) or re.match("\..*", text) or re.match(" +", text):
                                        if re.match(" .*", text) or re.match("\..*", text):
                                            text = text[1:]
                                        if re.match(" +", text):
                                            text = re.sub(' +', ' ', text)

                                    text = text.replace("\n","")
                                    text = text.replace("\r", "")
                                    text = text.replace("\t", "")
                                    speaker = re.sub(' +', ' ', speaker)
                                    speaker = speaker.replace("\n", "")
                                    speaker = speaker.replace("\r", "")
                                    speaker = speaker.replace("\t", "")

                                    parsed_paragraph = {"date": DATE,
                                                        "agenda": text_agenda_w_fase,
                                                        "speechnumber": speech_no,
                                                        "paragraphnumber": paragraph_no,
                                                        "speaker": speaker,
                                                        "party": party,
                                                        "text": text,
                                                        # There is only one element in that list, that's why taking the first element
                                                        "parliament": "IT-Parlamento",
                                                        "iso3country": "ITA",
                                                        "partyname": "",
                                                        "speakerrole": "",
                                                        "period": "",
                                                        "parliamentary_session": "",
                                                        "sitting": "",
                                                        }
                                    parsed_text.append(parsed_paragraph)
                    except Exception as e:
                        pass
            # Write parsed data
            parsed_doc_path = YEAR_PARSED_PATH.joinpath(f"{xmlfile}_parsed.csv")
            write_csv(parsed_doc_path,
                      data=parsed_text,
                      fieldnames=["date",
                                  "agenda",
                                  "speechnumber",
                                  "paragraphnumber",
                                  "speaker",
                                  "party",
                                  "text",
                                  "parliament",
                                  "iso3country",
                                  "partyname",
                                  "speakerrole",
                                  "period",
                                  "parliamentary_session",
                                  "sitting"])
        else:
            continue

'''
# THIS PART IS FOR YEAR 2017

for year in range(2009, 2017):
    YEAR_PATH = DATA_PATH.joinpath(str(year), "source")

    # Create the parsed directory
    try:
        YEAR_PARSED_PATH = PARSED_PATH.joinpath(str(year))
        os.mkdir(YEAR_PARSED_PATH)
    except Exception as e:
        print(e)

    for xmlfile in os.listdir(YEAR_PATH):
        # for xmlfile in ["/Users/mertozlutiras/Desktop/MEGA/MERT/work/NLP/eia-crawling/eia_crawling/spiders/data/national/italy/2016/source/20160104_543_session.xml"]:
        if xmlfile.endswith("xml"):

            # Define these for start
            speech_no = 0
            parsed_text = []

            tree = parse(str(YEAR_PATH.joinpath(xmlfile)))
            root = tree.getroot()

            # Date Found and Converted to the Format we seek
            locale.setlocale(locale.LC_TIME, "it_IT")
            dateElement = root.find("./metadati/dataEstesa")
            date = dateElement.text
            date_elems = date.split(" ")

            # Patch solution for some date type errors
            if len(date_elems) > 4:
                date = " ".join(date_elems[:4])

            # Another patch solution for dates of type "venerdi 1° dicembre 2017"
            if date_elems[1][-1] == "°":
                date_elems[1] = date_elems[1][:-1]
                date = " ".join(date_elems)

            try:
                date_object = datetime.strptime(date, "%A %d %B %Y")
            except Exception as e:
                print(xmlfile)
                print(e)

            # date is here, prepared in the correct form
            DATE = date_object.strftime("%Y-%m-%d")

            # Find and preprocess agendas then append them to their list
            agendas = root.findall("./resoconto/dibattito")
            agenda_list = []

            for agenda in agendas:
                # Find the agenda and preprocess it
                text_agenda = agenda.xpath("./titolo//text()")
                text_agenda = text_agenda[0].replace('\n\xa0', ' ')
                text_agenda = text_agenda.replace('\xa0', ' ')
'''