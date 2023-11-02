import pathlib
import textract
from sys import platform
from eia_crawling.spiders.utils import write_txt

SOURCE = 'source'

MONTHS = {"Ιανουαρίου": 1,
          "Φεβρουαρίου": 2,
          "Μαρτίου": 3,
          "Απριλίου": 4,
          "Μαΐου": 5,
          "Ιουνίου": 6,
          "Ιουλίου": 7,
          "Αυγούστου": 8,
          "Σεπτεμβρίου": 9,
          "Οκτωβρίου": 10,
          "Νοεμβρίου": 11,
          "∆εκεμβρίου": 12,
          "Δεκεμβρίου": 12}


def main():
    """
    Convert the pdfs to text data via OCR (tesseract)
    """

    # todo: Code is not operator system independent ==> \r\n on windows as line separator...
    if platform == 'linux':
        raise ValueError("Parsing for this OS not implemented")
    elif platform == 'win32':
        pass
    else:
        raise ValueError("Parsing for this OS not implemented")

    # Create paths
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'cyprus')
    raw_path = target_path.joinpath('raw')

    # pdf_p = list(raw_path.glob('*.pdf'))
    pdf_p = raw_path.joinpath('ΙΑ΄ Βουλευτική Περίοδος - Σύνοδος Δ΄ - (13.03.2019 - 31.07.2020).pdf')
    for index, session_p in enumerate([pdf_p]):
        data_encoded = textract.process(str(session_p), method='tesseract', language='grc')
        session_data = data_encoded.decode('UTF-8')
        write_txt(raw_path.joinpath(f"{session_p.stem}.txt"), session_data)


if __name__ == "__main__":
    main()
