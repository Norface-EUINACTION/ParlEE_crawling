import pathlib
import shutil
from argparse import ArgumentParser
from lxml import etree
from eia_crawling.spiders.utils import prepare_folder_national


def main():
    # Create paths
    data_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data')
    target_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'poland')

    # Prepare output structure
    prepare_folder_national(data_path, country='poland')

    ns = {'d': 'http://www.tei-c.org/ns/1.0'}

    # Create paths
    years_root_path = pathlib.Path(__file__).absolute().parent.parent.joinpath('spiders', 'data', 'national', 'poland', 'ppc-nanno', '')
    for house_dir in years_root_path.iterdir():
        if house_dir.stem == 'PPC_header' or house_dir.stem == '2015-2019':
            continue
        lower_house_dir = house_dir.joinpath('sejm', 'posiedzenia')
        for session_dir in lower_house_dir.iterdir():
            for sitting_dir in session_dir.iterdir():
                sitting_src_p = sitting_dir.joinpath('text_structure.xml')
                sitting_meta_src_p = sitting_dir.joinpath('header.xml')
                sitting_meta_src = etree.parse(str(sitting_meta_src_p))
                # Get the year from the src path
                year = sitting_meta_src.xpath('//d:date/text()', namespaces=ns)[0][:4]
                if int(year) < 2009:
                    continue
                sitting_trg_file_name = sitting_dir.stem + '_' + 'text_structure.xml'
                sitting_meta_trg_file_name = sitting_dir.stem + '_' + 'header.xml'
                sitting_trg_p = target_path.joinpath(year, 'source', sitting_trg_file_name)
                sitting_meta_trg_p = target_path.joinpath(year, 'source', sitting_meta_trg_file_name)
                shutil.copy(str(sitting_src_p), str(sitting_trg_p))
                shutil.copy(str(sitting_meta_src_p), str(sitting_meta_trg_p))


if __name__ == "__main__":
    main()
