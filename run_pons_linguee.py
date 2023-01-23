import time
from typing import Optional
import pandas as pd
from dict_combine import DictCombine
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

FINAL_COLS = ["German", "Picture", "English", "Audio", "Sample sentence", 
              "Plural and inflected forms", "German Alternatives", 
              "English Alternatives", "Part of speech", "original_word",
              "Source"]

def get_reactor_df():
    files = [x for x in Path(".").glob("lln_excel_items_*.xlsx")]
    dates = [pd.to_datetime(str(f).split("_")[-2]) for f in files]
    files = [x for _, x in sorted(zip(dates, files), reverse=True)]
    reactor_df = pd.read_excel("lln_excel_items_2022-10-6_8170477.xlsx")
    cols_to_keep = ["Item type", "Subtitle", "Translation", "Word", "Lemma", "Word definition", "Part of speech"]
    new_cols = ["item_type", "subtitle", "translation", "word", "lemma", "definition", "part_of_speech"]
    col_map = {x: y for x, y in zip(cols_to_keep, new_cols)}
    reactor_df = reactor_df[cols_to_keep]
    reactor_df.rename(columns=col_map, inplace=True)
    return reactor_df


def prepare_csv(csv: str):
    df = pd.read_csv(csv, header=None, names=["word", "part_of_speech"])
    df["lemma"] = df.word
    df["item_type"] = "Word"
    df["subtitle"] = ""
    df["translation"] = ""
    return df


def run(csv: Optional[str] = None, save_csv: str = "ready_for_anki.csv"):
    if csv is None:
        df = get_reactor_df()
        source = "Language Factory"
    else:
        df = prepare_csv(csv)
        source = "manual"

    try:
        ready_for_anki = pd.read_csv(save_csv, names=FINAL_COLS, header=None)
    except FileNotFoundError:
        ready_for_anki = pd.DataFrame()
    ready_entries = []
    for ix, row in df.loc[df.item_type == "Word"].iterrows():
        print(ix)
        print(row.word)
        
        # 42
        if ix < 43:
            continue

        if not ready_for_anki.empty:
#             import pdb; pdb.set_trace()
            if row.lemma.lower() in ready_for_anki.original_word.to_list():
                continue
        example_src = row.subtitle if "..." not in row.subtitle else ""
        example_dst = row.translation if "..." not in  row.translation else ""
        ready_entry = DictCombine.init(word=row.lemma,
                                       input_lang="de",
                                       dicts_to_use=["pons", "linguee"],
                                       pos=row.part_of_speech.lower(),
                                       external_example_dst=example_dst,
                                       external_example_src=example_src,
                                       source=source
                                       )
    #     import pdb; pdb.set_trace()
        ready_entry, errors = ready_entry()
        if not ready_entry:
            print(f"No entry for {row.word}")
            continue
        if "503" in errors:
            raise TooManyRequestsError("Linguee too many requests error.")
        ready_entries.append(ready_entry)
        time.sleep(10)
        if ix % 10 == 1:
#             import pdb; pdb.set_trace()
            df_tmp = pd.DataFrame(ready_entries)
            ready_entries = []
            ready_for_anki = ready_for_anki.append(df_tmp)
            ready_for_anki.to_csv(save_csv, index=False)
    df_tmp = pd.DataFrame(ready_entries)
    ready_for_anki = ready_for_anki.append(df_tmp)
    ready_for_anki.to_csv(save_csv, index=False)

if __name__ == "__main__":
    run(save_csv="ready_for_anki3.csv")
