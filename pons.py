import requests
import json
from dict_secrets import PONS_SECRET
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd


class PonsEntries():
    def __init__(self,
                 word: str,
                 src_lang: str = "en",
                 dst_lang: str = "de",
                 ):
        self.url = f"https://api.pons.com/v1/dictionary?l={dst_lang}{src_lang}&q={word}"
        self.entries = self.get_entries()
        self.langs = [x['lang'] for x in self.entries]
        self._init_processed()
        self.process_entries()

    def get_entries(self):
        if r := requests.get(self.url, headers={"X-Secret": PONS_SECRET}).text:
            return json.loads(r)
        else:
            return r

    def _init_processed(self):
        self.processed_entries = {}
        for lang in self.langs:
            self.processed_entries[lang] = defaultdict(list)

    def process_entries(self):
        for entry in self.entries:
            lang = entry["lang"]
            for iy, hit in enumerate(entry["hits"]):
                roms = hit["roms"]
                entries_n = 0
            # roms = entry["hits"][0]["roms"]
                for ix, rom in enumerate(roms):
                    arabs = rom["arabs"]
                    arabs_n = len(arabs)
                    entries_n += arabs_n
                    self.processed_entries[lang]["hit"].extend([ix] * arabs_n)
                    self.process_headwords(lang=lang, rom=rom, n=arabs_n)
                    self.process_headword_full(lang=lang, rom=rom, n=arabs_n)
                    wc = self.process_wordclass(lang=lang, rom=rom, n=arabs_n)
                    for arab in arabs:
                        self.process_arab(lang=lang, arab=arab, wc=wc)

                self.processed_entries[lang]["entry"].extend([iy] * entries_n)

    def process_headwords(self, lang: str, rom: dict, n: int):
        self.processed_entries[lang]["headword"].extend([rom["headword"]] * n)

    def process_headword_full(self, lang: str, rom: dict, n: int):
        hf = rom["headword_full"]
        hf = BeautifulSoup(hf, features="lxml")
        if span := hf.find("span", {"class": "flexion"}):
            flexion = span.text
        else:
            flexion = ""
        if span := hf.find("span", {"class": "phonetics"}):
            phonetics = span.text
        else:
            phonetics = ""
        if span := hf.find("span", {"class": "genus"}):
            if acronym := span.find("acronym"):
                gender = acronym.get("title")
            else:
                gender = span.get("title")
            if not gender:
                gender = span.text
        else:
            gender = ""
        # if span := hf.find("span", {"class": "wordclass"}):
        #     pos = span.acronym.get("title")
        # else:
        #     pos = ""
        self.processed_entries[lang]["flexion"].extend([flexion] * n)
        self.processed_entries[lang]["phonetics"].extend([phonetics] * n)
        self.processed_entries[lang]["gender_src"].extend([gender] * n)

    def process_wordclass(self, lang: str, rom: dict, n: int):
        if wordclass := rom.get("wordclass", ""):
            self.processed_entries[lang]["pos"].extend([wordclass] * n)
            return wordclass
        else:
            raise KeyError("wordclass")

    def process_arab(self, lang: str, arab: dict, wc: str):
        # Sens
        sens = BeautifulSoup(arab["header"], features="lxml")
        if span := sens.find("span", {"class": "sense"}):
            sense = span.text
        else:
            sense = ""
        self.processed_entries[lang]["sense"].append(sense)
        # if wc != "noun":
        #     __import__('pdb').set_trace()

        # Translation
        trans = BeautifulSoup(arab["translations"][0]["target"], features="lxml")
        target = trans.text
        gender = ""
        if wc == "noun" and lang in ["en"]:  # TODO tmp solution, works only if we translate from english to a language that has noun genders
            sp = target.split()
            target = " ".join(sp[:-1])
            gender = sp[-1]
        if span := trans.find("span"):
            target_desc = span.acronym.get("title")
        elif acronym := trans.acrronym:
            target_desc = acronym.get("title")
        else:
            target_desc = ""
        self.processed_entries[lang]["target"].append(target)
        self.processed_entries[lang]["gender_dst"].append(gender)
        self.processed_entries[lang]["target_desc"].append(target_desc)

        # Examples
        examples_src1 = []
        examples_src2 = []
        examples_dst1 = []
        examples_dst2 = []
        for tran in arab["translations"][1:]:
            src = BeautifulSoup(tran["source"], features="lxml")
            src = src.text

            dst = BeautifulSoup(tran["target"], features="lxml")
            dst = dst.text
            if target.lower() in [x.lower() for x in dst.split()]:
                examples_src1.append(src.strip())
                examples_dst1.append(dst.strip())
            else:
                examples_src2.append(src.strip())
                examples_dst2.append(dst.strip())
        examples_src = examples_src1 + examples_src2
        examples_dst = examples_dst1 + examples_dst2
        # es = ""
        # ed = ""
        # for ix, (exs, exd) in enumerate(zip(examples_src[:2],
        #                                     examples_dst[:2])):
        #     if ix != len(examples_dst[:2]):
        #         es += f"{ix}. {exs}"

        self.processed_entries[lang]["examples_src"].append("<br>".join(examples_src[:2]))
        self.processed_entries[lang]["examples_dst"].append("<br>".join(examples_dst[:2]))

    def get_df(self):
        df = pd.DataFrame()
        for k, v in self.processed_entries.items():
            # for kk, vv in v.items():
            #     print(kk)
            #     print(len(vv))
            # __import__('pdb').set_trace()

            df_tmp = pd.DataFrame(v)
            df_tmp["lang"] = k
            df = pd.concat([df, df_tmp])
        return df

    def __call__(self):
        return self.get_df()

