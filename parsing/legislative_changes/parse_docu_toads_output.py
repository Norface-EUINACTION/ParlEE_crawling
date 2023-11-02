import pathlib
import pandas as pd
from argparse import ArgumentParser

EDIT_OPERATIONS = ['substitution', 'addition', 'deletion', 'transposition']


def main(data_dir: str):
    """
    This function performs post-processing on raw output from DocuToads algorithm. DocuToads output is token-based
    and the goal is to combine tokens back into text and identify the change with the surrounding context. Following
    heuristic applies: change is defined as a sequence of tokens marked with one of edit operations( 'substitution',
    'addition', 'deletion', 'transposition') with preceding and succeeding sequence of unchanged tokens:
    change = UNCHANGED_SEQUENCE CHANGED_SEQUENCE CHANGED_SEQUENCE

    :param data_dir: directory to DocuToads outputs
    :return: csv files for each document pair
    """
    for doc in pathlib.Path(data_dir).iterdir():
        data = pd.read_csv(doc, sep=';')
        data['change'] = data['Edit operation'].apply(lambda x: 1 if x in EDIT_OPERATIONS else 0)
        data['Removed or substituted word'] = data['Removed or substituted word'].fillna('').astype(str)
        data['Word in both texts'] = data['Word in both texts'].fillna('').astype(str)
        data['Added or substituted word'] = data['Added or substituted word'].fillna('').astype(str)

        # Get the starting position of each 0 and 1
        indices = {}
        current_val = None
        for idx, row in data.iterrows():
            if row['change'] == 0 and current_val != 0:
                current_val = 0
                indices[idx] = row['change']
            elif row['change'] == 1 and current_val != 1:
                current_val = 1
                indices[idx] = row['change']

        # Sequence pattern [0,1,0,1]
        pattern = [0, 1, 0, 1]
        keys, values = list(indices.keys()), list(indices.values())
        n = len(pattern)
        subseq_val = zip(*(values[i:] for i in range(n)))
        subseq_k = zip(*(keys[i:] for i in range(n)))
        subseq = zip(subseq_val, subseq_k)
        subseq = list(subseq)

        changes = []
        for s in subseq:
            if s[0] == tuple(pattern):
                changes.append(s[1])

        # That would give as 3 idx: e.g. 0, 12, 24, 52 allowing for compiling the change
        # 0-12 --> same words
        # 12-24 --> change
        # 24-52 --> same words
        dct = []
        for c in changes:
            same_words_1 = data[c[0]:c[1]]
            alteration = data[c[1]:c[2]]
            same_words_2 = data[c[2]:c[3]]

            sw_1 = same_words_1.groupby('change')['Word in both texts'].agg(' '.join)[0].strip()
            sw_2 = same_words_2.groupby('change')['Word in both texts'].agg(' '.join)[0].strip()

            alter_old = alteration.groupby('change')['Removed or substituted word'].apply(' '.join)[1].strip()
            alter_new = alteration.groupby('change')['Added or substituted word'].apply(' '.join)[1].strip()

            dct.append((' '.join([sw_1, alter_old, sw_2]), ' '.join([sw_1, alter_new, sw_2])))

        df = pd.DataFrame(dct, columns=['proposal', 'final_act'])
        file_name = doc.stem[:13]
        df.to_csv(
            pathlib.Path(__file__).absolute().parent.joinpath('outputs', 'regular', file_name).with_suffix('.csv'))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("data_dir", type=str,
                        help="Directory to DocuToads outputs")
    args = parser.parse_args()
    data_dir = args.data_dir
    main(data_dir=data_dir)
