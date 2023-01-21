import os
import requests
import json
from dict_secrets import PONS_SECRET
from typing import List, Optional
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
import shutil
from copy import copy
from urllib3.exceptions import MaxRetryError, NewConnectionError

from pathlib import Path
from utils import pos_processors, word_processing, noun_processing, verb_processing
from dict_base import DictBase

import linguee_api


def process_lang(lang: str):
    lang = lang.lower()
    if "english" in lang:
        return "en"
    if "german" in lang:
        return "de"


class LingueeEntries():
    def __init__(self,
                 word: str,
                 src_lang: str = "en",
                 dst_lang: str = "de",
                 ):
        self.word = word
        self.api_url = self.get_api_url()
        self.url = f"{self.api_url}/api/v2/translations?query={word}&src={src_lang}&dst={dst_lang}&guess_direction=true&follow_corrections=always"
        print(self.url)
        self.lang_pool = [src_lang, dst_lang]
        self.entries, self.error = self._get_lin_entries()
        self.langs = [self._get_lang(x) for x in self.entries]
        self._init_processed()
        self.process_entries()

    def get_api_url(self):
        try:
            r = requests.get("http://127.0.0.1:8000")
            r = r.ok
        # except (ConnectionError, MaxRetryError, ConnectionRefusedError, NewConnectionError):
        except:
            r = False
        if not r:
            os.system("uvicorn linguee_api.api:app &")
        return "http://127.0.0.1:8000"

    def _get_lin_entries(self):
        r = requests.get(self.url).text
        if r == "Internal Server Error":
            return {}, True
        return json.loads(r), False

    def _get_lang(self, entry):
        lang_pool = copy(self.lang_pool)
        if audio_links := entry.get("audio_links", []):
            for al in audio_links:
                if lang := al.get("lang"):
                    return process_lang(lang)
        for trans in entry["translations"]:
            if audio_links := trans.get("audio_links", []):
                for al in audio_links:
                    if lang := al.get("lang"):
                        lang_pool.remove(process_lang(lang))
                        return lang_pool[0]
        # raise KeyError(f"Couldn't find a language for word: {self.word}")
        print(f"Couldn't find a language for word: {self.word}")
        return ""

    def _init_processed(self):
        self.processed_entries = {}
        for lang in self.langs:
            self.processed_entries[lang] = defaultdict(list)

    def process_entries(self):
        for ix, entry in enumerate(self.entries):
            lang = self._get_lang(entry)
            word = entry["text"]
            pos = entry["pos"]
            forms = entry["forms"]
            grammar_info = entry["grammar_info"]
            audio = self._get_audio(entry)

            trans = entry["translations"]
            trans_n = len(trans)
            
            self.processed_entries[lang]["headword"].extend([word] * trans_n)
            self.processed_entries[lang]["entry"].extend([ix] * trans_n)
            self.processed_entries[lang]["pos"].extend([pos] * trans_n)
            self.processed_entries[lang]["forms"].extend([forms] * trans_n)
            self.processed_entries[lang]["grammar_info"].extend([grammar_info] * trans_n)
            self.processed_entries[lang]["audio_src"].extend([audio] * trans_n)
            for trans in trans:
                audio_dst = self._get_audio(trans)
                pos = trans["pos"]
                target = trans["text"]
                self.processed_entries[lang]["audio_dst"].append(audio_dst)
                self.processed_entries[lang]["pos_dst"].append(pos)
                self.processed_entries[lang]["target"].append(target)
                self.process_examples(trans, lang)

    def _get_audio(self, entry: dict):
        if audio_links := entry.get("audio_links", []):
            for al in audio_links:
                if audio := al.get("url"):
                    return audio
        return ""

    def process_examples(self, trans: dict, lang: str):
        examples = trans["examples"]
        # Examples
        examples_src = []
        examples_dst = []
        for example in examples[:2]:
            examples_src.append(example["src"])
            examples_dst.append(example["dst"])

        self.processed_entries[lang]["examples_src"].append("<br>".join(examples_src))
        self.processed_entries[lang]["examples_dst"].append("<br>".join(examples_dst))

    def get_df(self):
        if not self.error:
            df = pd.DataFrame()
            for k, v in self.processed_entries.items():
                # for kk, vv in v.items():
                #     print(kk)
                #     print(len(vv))
                # __import__('pdb').set_trace()

                df_tmp = pd.DataFrame(v)
                df_tmp["lang"] = k
                df = pd.concat([df, df_tmp])
            df["gender_src"] = ""
            df["gender_dst"] = ""
            for ix, row in df.iterrows():
                if "," in row.pos:
                    pg = [x.strip() for x in row.pos.split(",")]
                    df.loc[ix, "pos"], df.loc[ix, "gender_src"] = pg
                if "," in row.pos_dst:
                    pg = [x.strip() for x in row.pos_dst.split(",")]
                    df.loc[ix, "pos_dst"], df.loc[ix, "gender_dst"] = pg
            return df
        else:
            return pd.DataFrame()

    def __call__(self):
        return self.get_df()


def get_lin_entries(word):
    r = requests.get(word).text
    if r == "Internal Server Error":
        return "Linguee Error"
    return json.loads(r)


if __name__ == "__main__":
    import pickle
    word = "schreiben"
    src_lang = "de"
    dst_lang = "en"
    le = LingueeEntries(word)
    import pdb; pdb.set_trace()
    df = LingueeEntries(word)()
    # with open("lin_trans.pkl", "wb") as f:
    #     pickle.dump(entries, f)
    # with open("lin_trans.pkl", "rb") as f:
    #     trans_entries = pickle.load(f)
    # entries = LingueeEntries(trans_entries, word)
    print(df.iloc[1])
    print(df.iloc[1]["forms"])
