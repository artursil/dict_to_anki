from abc import ABC, abstractmethod
import requests
import json
from dict_secrets import PONS_SECRET
from typing import List, Optional
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
import shutil

from pathlib import Path
from simple_image_download import simple_image_download as simp
response = simp.simple_image_download


def downloadimages(query):
    # keywords is the search query
    # format is the image file format
    # limit is the number of images to be downloaded
    # print urs is to print the image file url
    # size is the image size which can
    # be specified manually ("large, medium, icon")
    # aspect ratio denotes the height width ratio
    # of images to download. ("tall, square, wide, panoramic")
    query = query.split(",")[0]
    response().download(query, 10)
    image = Path.cwd() / "simple_images" / query
    files = list(image.glob("*"))
    file = [x for x in files if x.stat().st_size > 10000][0]    
    for f in files:
        if f != file:
            f.unlink()
    return file


DER_DIE_DAS = {"masculine": "der",
               "neuter": "das",
               "feminine": "die",
               "m": "der",
               "nt": "das",
               "f": "die",
               "plural": "die"}


def word_processing(word: str, sense: str):
    return word.replace("·", "") + sense


def de_verb_processing(verb: str, **kwargs):
    pos = kwargs.get("pos")
    if pos == "reflexive verb":
        verb = f"sich {verb}"
    return verb


def en_verb_processing(verb: str, **kwargs):
    if "to " in verb:
        return verb
    return f"to {verb}"


verb_processors = {
    "de": de_verb_processing,
    "en": en_verb_processing,
}


def verb_processing(verb: str, lang: str, pos: str):
    return verb_processors[lang](verb, pos=pos)


def de_noun_processing(noun: str, **kwargs):
    gender = kwargs.get("gender", "")
    return f"{DER_DIE_DAS[gender]} {noun.capitalize()}"


def en_noun_processing(noun: str, **kwargs):
    return noun


noun_processors = {
    "de": de_noun_processing,
    "en": en_noun_processing,
}


def noun_processing(noun: str, lang: str, gender: str):
    return verb_processors[lang](noun, gender=gender)


def de_pos_processing(pos: str, **kwargs):
    word = kwargs.get("word", "")
    if "verb" in pos:
        if "sich" in word.split():
            pos = "reflexive verb"
        else:
            pos = "transitive verb"
    return pos


def en_pos_processing(pos: str, **kwargs):
    return pos


pos_processors = {
    "de": de_pos_processing,
    "en": en_pos_processing,
}


def pos_processing(pos: str, lang: str, word: str):
    pos = pos.lower()
    pos_map = {"adj": "adjective", "adv": "adverb"}
    pos = pos_map[pos] if pos in pos_map.keys() else pos
    return pos_processors[lang](pos, word=word)


class DictFactory(ABC):
    def __init__(self, original_word: str,
                 pos: Optional[str],
                 input_lang: Optional[str],
                 src_lang: str,
                 dst_lang: str,
                 source: str,
                 collections_path: Path = Path("~/.local/share/Anki2/User 1/collection.media")):
        self.original_word = original_word
        self.original_pos = pos
        self.input_lang = input_lang
        self.src_lang = src_lang
        self.dst_lang = dst_lang
        self.source = source
        self.collections_path = collections_path.expanduser()

    @abstractmethod
    def get_entries():
        pass

    @property
    def image(self):
        if self.input_lang == self.dst_lang:
            img_word = self.definition
        else:
            img_word = self.word
        image_path = downloadimages(img_word)
        img_name = image_path.parent.stem + image_path.suffix
        img_dst = self.collections_path / img_name
        shutil.copy(image_path, img_dst)
        return f"<img src='{img_name}'>"

    @property
    @abstractmethod
    def definition(self):
        pass

    @property
    @abstractmethod
    def example_src(self):
        pass

    @property
    @abstractmethod
    def audio(self):
        pass

    @property
    @abstractmethod
    def example_dst(self):
        pass

    @property
    @abstractmethod
    def tenses_plural(self):
        pass

    @property
    @abstractmethod
    def pos(self):
        pass

    @property
    @abstractmethod
    def word(self):
        pass

    def anki_row(self):
        if self.input_lang == self.src_lang:
            processed_word = self.definition
        else:
            processed_word = self.word

        row_dict = {
            "German": processed_word,
            "Picture": self.image,
            "English": self.definition,
            "Audio": self.audio,
            "Sample sentence": self.example_src,
            "Plural and inflected forms": self.tenses_plural,
            "German Alternatives": "",
            "English Alternatives": self.example_dst,
            "Part of speech": self.pos,
            "original_word": self.word,
            "Source": self.source
        }
        return row_dict


class PonsEntries():
    def __init__(self, entries: List[dict]):
        self.entries = entries
        self.langs = [x['lang'] for x in self.entries]
        self._init_processed()
        self.process_entries()

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
                    self.processed_entries[lang]["rom_n"].extend([ix] * arabs_n)
                    self.process_headwords(lang=lang, rom=rom, n=arabs_n)
                    self.process_headword_full(lang=lang, rom=rom, n=arabs_n)
                    wc = self.process_wordclass(lang=lang, rom=rom, n=arabs_n)
                    for arab in arabs:
                        self.process_arab(lang=lang, arab=arab, wc=wc)

                self.processed_entries[lang]["hit_n"].extend([iy] * entries_n)

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
            gender = span.get("title")
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
        self.processed_entries[lang]["gender_dst_dst"].append(gender)
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


# class PonsDict(DictFactory):
#     def __init__(self,
#                  word: str,
#                  pos: Optional[str] = None,
#                  input_lang: Optional[str] = None,
#                  manual_selection: bool = False,
#                  src_lang: str = "en",
#                  dst_lang: str = "de"):
#         self.original_word = word
#         self.original_pos = pos
#         self.input_lang = input_lang
#         self.manual_selection = manual_selection
#         self.src_lang = src_lang
#         self.dst_lang = dst_lang
#
#         self.api = f"https://api.pons.com/v1/dictionary?l={target_lang}{src_lang}&q={word}"
#         self.processed_entries = PonsEntries(self.entries)
#
#     @property
#     def row(self):
#         entries = self.entries
#         if self.original_pos is None:
#             pass
#
#             
#
#     def get_entries(self):
#         if r := requests.get(self.api, headers={"X-Secret": PONS_SECRET}).text:
#             return json.loads(r)
#         else:
#             return r
#
#     @property
#     def entries():
#         pons = PonsEntries(self.get_entries())
#         df = pons.get_df()
#         return df
#
#     def definition(self):
#         pass
#
#     def example_src(self):
#         pass
#
#     def audio(self):
#         pass
#
#     @property
#     def example_dst(self):
#         pass
#
#     @property
#     def tenses_plural(self):
#         pass
#
#     @property
#     def pos(self):
#         pass
#
#     @property
#     def word(self):
#         pass
#
#
# class PonsDeEn(PonsDict):
#     def __init__(self,
#                  word: str,
#                  input_lang: Optional[str] = None,
#                  pos: Optional[str] = None):
#         super().__init__(word, pos, input_lang, "en", "de")
#
#     def definition(self):
#         definition = word_processing(self.row.target)
#         lang = self.src_lang if self.src_lang != self.input_lang else \
#             self.dst_lang
#         if "verb" in self.pos:
#             word = verb_processing(verb=word,
#                                    lang=lang,
#                                    pos=self.pos,
#                                    )
#         if self.pos == "noun":
#             word = noun_processing(noun=word,
#                                    lang=lang,
#                                    gender=self.row.gender_src,
#                                    )
#
#     def example_src(self):
#         return self.row.examples_src
#
#     def audio(self):
#         pass
#
#     @property
#     def example_dst(self):
#         return self.row.examples_dst
#
#     @property
#     def tenses_plural(self):
#         return self.row.flexion
#
#     @property
#     def pos(self):
#         if self.pos is None:
#             self.pos = self.row.pos
#
#     @property
#     def input_lang(self):
#         if self.input_lang is None:
#             self.input_lang = self.row.lang
#
#     @property
#     def word(self):
#         word = word_processing(self.original_word, sense=self.row.sense)
#         if "verb" in self.pos:
#             word = verb_processing(verb=word,
#                                    lang=self.input_lang,
#                                    pos=self.pos,
#                                    )
#         if self.pos == "noun":
#             word = noun_processing(noun=word,
#                                    lang=self.input_lang,
#                                    gender=self.row.gender_src,
#                                    )
#         return word

class PonsDict(DictFactory):
    def __init__(self,
                 word: str,
                 pos: Optional[str] = None,
                 input_lang: Optional[str] = None,
                 manual_selection: bool = False,
                 src_lang: str = "en",
                 dst_lang: str = "de",
                 source: str = "manual",
                 # collections_path: Path,
                 ):
        super().__init__(word, pos, input_lang, src_lang, dst_lang, source)
        self.manual_selection = manual_selection

        self.api = f"https://api.pons.com/v1/dictionary?l={dst_lang}{src_lang}&q={word}"
        self.entries = self.process_entries()
        self.input_lang = self.get_input_lang(self.input_lang)
        # self.processed_entries = PonsEntries(self.entries)

    @property
    def row(self) -> pd.Series:
        df = self.entries
        if self.original_pos is not None:
            pos = pos_processing(pos=self.original_pos, lang=self.dst_lang,
                                 word=self.original_word)
            if row := df.loc[df.pos.isin(pos)]:
                return row.iloc[0]
        return df.iloc[0]

    def get_entries(self):
        if r := requests.get(self.api, headers={"X-Secret": PONS_SECRET}).text:
            return json.loads(r)
        else:
            return r

    def process_entries(self):
        pons = PonsEntries(self.get_entries())
        df = pons.get_df()
        return df

    @property
    def audio(self):
        ""

    @property
    def definition(self):
        definition = word_processing(self.row.target, "")
        lang = self.src_lang if self.src_lang != self.input_lang else \
            self.dst_lang
        if "verb" in self.pos:
            definition = verb_processing(verb=definition,
                                         lang=lang,
                                         pos=self.pos,
                                         )
        if self.pos == "noun":
            definition = noun_processing(noun=definition,
                                         lang=lang,
                                         gender=self.row.gender_src,
                                         )
        return definition

    @property
    def example_src(self):
        return self.row.examples_src

    @property
    def example_dst(self):
        return self.row.examples_dst

    @property
    def tenses_plural(self):
        return self.row.flexion

    @property
    def pos(self):
        if self.original_pos is None:
            return self.row.pos

    def get_input_lang(self, input_lang):
        if input_lang is None:
            return self.row.lang
        return input_lang

    @property
    def word(self):
        word = word_processing(self.original_word, sense=self.row.sense)
        if "verb" in self.pos:
            word = verb_processing(verb=word,
                                   lang=self.input_lang,
                                   pos=self.pos,
                                   )
        if self.pos == "noun":
            word = noun_processing(noun=word,
                                   lang=self.input_lang,
                                   gender=self.row.gender_src,
                                   )
        return word


if __name__ == "__main__":
    pons = PonsDict("laufen")
    # print(pons.entries)
    entries = pons.entries
    # entries = PonsEntries(entries)
    anki_row = pons.anki_row()
    # df = pons.get_df()
    # df.to_csv("test_pons.csv")
    print(anki_row)
    __import__('pdb').set_trace()

