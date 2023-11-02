from SPARQLWrapper import SPARQLWrapper, CSV

import pathlib
import unicodedata
import io
import pandas as pd
import json


def main():
    """
    Query the data from the talk of europe database
    """

    # Create paths
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'ep', 'talk_of_europe')

    sparql = SPARQLWrapper("http://linkedpolitics.ops.few.vu.nl/sparql/")

    offset = 0
    limit = 50000

    data = pd.DataFrame()

    # Define strings
    while True:
        query_string_1 = """
            SELECT DISTINCT ?date ?agendanumber ?agenda ?speechnumber ?speaker ?party ?national_party ?mep_id ?original_text ?language ?translated_text ?mode
            WHERE { 
               ?sessionday rdf:type lpv_eu:SessionDay.
               ?sessionday dcterms:date ?date.	
               ?sessionday dcterms:hasPart ?agendaitem.
               ?agendaitem dcterms:hasPart ?speech.
            
               ?speech lpv:speaker ?member.
               ?member rdf:type lpv:MemberOfParliament.
               ?member foaf:name ?speaker.
            
               ?speech lpv:spokenText ?original_text.
               ?speech lpv:docno ?speechnumber.   
            
               ?agendaitem lpv:docno ?agendanumber.

               OPTIONAL{
                 ?speech dcterms:language ?language.
               }
            
               OPTIONAL{
                 ?agendaitem dcterms:title ?agenda.
                 FILTER (langMatches(lang(?agenda), "en"))
               }
                
               OPTIONAL{
                 ?speech lpv:spokenAs ?function_eu.
                 ?function_eu lpv:institution ?eu_institution.
                 ?eu_institution rdf:type lpv:EUParty.
                 ?eu_institution lpv:acronym ?party.
                }
    
               OPTIONAL{
                 ?speech lpv:spokenAs ?function_national.
                 ?function_national lpv:institution ?national_institution.
                 ?national_institution rdf:type lpv:NationalParty.
                 ?national_institution rdfs:label ?national_party.
               } 
                
               OPTIONAL{
                 ?member lpv:MEP_ID ?mep_id.
               }
               
               OPTIONAL{
                 ?speech lpv:translatedText ?translated_text.
                 FILTER (langMatches(lang(?translated_text), "en"))
               }
               
               FILTER ( ?date >= "2009-01-01"^^xsd:date && ?date <= "2019-12-31"^^xsd:date )
              } ORDER BY ?speechnumber
        """
        # ORDER BY ?date ?agendanumber ?speechnumber
        limit_string = f" LIMIT {limit} OFFSET {offset}"

        sparql.setQuery(query_string_1 + limit_string)

        # Info: There are less than 350000 speeches to query
        sparql.setReturnFormat(CSV)
        sparql.addParameter("resourceFormat", "ns")
        sparql.addParameter("entailment", "none")
        results = sparql.query().convert()

        results = results.decode('UTF-8')

        data_tmp = pd.read_csv(io.StringIO(results))
        data = data.append(data_tmp)

        if data_tmp.index.size < limit:
            break
        else:
            offset += limit

    def clean_text(x: str):
        if isinstance(x, str):
            x = x.replace('\n', ' ')
            x = unicodedata.normalize("NFKD", x)
        return x

    data.loc[:, "original_text"] = data.original_text.apply(clean_text)
    data.loc[:, "translated_text"] = data.translated_text.apply(clean_text)

    # If the statement is not written it is spoken
    data.loc[:, "mode"] = data.loc[:, "mode"].fillna("spoken")

    file_name = "talk_of_europe_2009_2017_raw.csv"
    data.to_csv(target_path.joinpath(file_name), index=False)


if __name__ == "__main__":
    main()
