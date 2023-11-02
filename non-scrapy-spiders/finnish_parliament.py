import requests
import pathlib
from .utils import (write_source_doc, prepare_folder_national)

# Define string constants
COUNTRY = 'finland'
FULL_TITLE = 'full_title'
FILING_DATE = 'filing_date'
URL = 'URL'
SOURCE = 'source'
REPORT = 'session'
NATIONAL = 'national'

ROOT = pathlib.Path(__file__).absolute().parent.parent
DATA = ROOT.joinpath("spiders","data")

prepare_folder_national(DATA, COUNTRY)

year_upper_lims_dict = {2019:87, 2018:181, 2017:147, 2016:139, 2015:85}

for year, upper_lim in year_upper_lims_dict.items():
   for number in range(1,upper_lim+1):
	   try:
	        url = f'https://www.eduskunta.fi/FI/vaski/Poytakirja/Documents/PTK_{number}+{year}.pdf'
	        response = requests.get(url)
	        path = DATA.joinpath(NATIONAL, COUNTRY, str(year), SOURCE, f'{number}.pdf')
	        write_source_doc(path, response.content)
	   except Exception as e:
	        print(e)