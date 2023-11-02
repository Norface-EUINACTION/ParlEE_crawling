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

    data = pd.DataFrame()

    loc_path = pathlib.Path.cwd().joinpath("localization")
    in_writing_list = []
    for filepath in loc_path.glob('*.json'):
        with open(str(filepath), mode="r", encoding="utf-8") as jfile:
            content = jfile.read()
        vars = json.loads(content)
        in_writing_list.append(vars['in_writing'])

    in_writing_test = "|".join(in_writing_list)

    # Define strings
    for year in range(2009, 2018):
        query_string_1 = """
            SELECT DISTINCT ?speechnumber ?mode
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
                
                   ?speech lpv:docno ?speechnumber.
               """
        in_writing_string = 'OPTIONAL {?speech lpv:unclassifiedMetadata ?metadata. FILTER (regex(?metadata, "' + in_writing_test + '", "i")). BIND(IF(BOUND(?metadata), "written", "spoken") as ?mode)}'
        filter_string = f"FILTER ( ?date >= '{year}-01-01'^^xsd:date && ?date <= '{year}-12-31'^^xsd:date )"
        end_string = "}"

        sparql.setQuery(query_string_1 + in_writing_string + filter_string + end_string)

        # Info: There are less than 350000 speeches to query
        sparql.setReturnFormat(CSV)
        sparql.addParameter("resourceFormat", "ns")
        sparql.addParameter("entailment", "none")
        results = sparql.query().convert()

        results = results.decode('UTF-8')

        data_tmp = pd.read_csv(io.StringIO(results))
        data = data.append(data_tmp)

    data.loc[:, "mode"] = data.loc[:, "mode"].fillna("spoken")

    file_name = "talk_of_europe_2009_2017_written_flag.csv"
    data.to_csv(target_path.joinpath(file_name), index=False)


if __name__ == "__main__":
    main()
