from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import pathlib
import os

ROOT = pathlib.Path(__file__).absolute().parent.parent
DATA_PATH = ROOT.joinpath("spiders","data","national","greece")

if not os.path.isdir(DATA_PATH):
    os.mkdir(DATA_PATH)


chrome_options = Options()
chrome_options.add_argument("--headless")
CHROME_PATH = "/usr/local/bin/chromedriver"

prefs = {"download.default_directory": str(DATA_PATH.absolute())}
chrome_options.add_experimental_option("prefs",prefs)

driver = webdriver.Chrome(CHROME_PATH,options=chrome_options)
for i in range(31,44):
    driver.get(f'https://www.hellenicparliament.gr/en/Praktika/Synedriaseis-Olomeleias?pageNo={i}')

    WebDriverWait(driver,10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="pagecontent"]/table/tbody')))
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    for j in range(1,11):
        j = str(j)
        if len(j) == 1:
            j = "0"+j
        row = driver.find_element_by_id(f'ctl00_ContentPlaceHolder1_rr_repSearchResults_ctl{j}_lnkTxt')
        row.click()
        time.sleep(2)
    time.sleep(1)