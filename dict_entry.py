from typing import Optional
import pandas as pd
import shutil

from pathlib import Path
from utils import (get_audio, pos_processing, word_processing, noun_processing, 
                   verb_processing, downloadimages)
from dict_base import DictBase
from linguee import LingueeEntries
from pons import PonsEntries


entries_factory = {
    "pons": PonsEntries,
    "linguee": LingueeEntries,
}


class DictEntry():
    def __init__(self,
                 word: str,
                 pos: Optional[str] = None,
                 input_lang: Optional[str] = None,
                 manual_selection: bool = False,
                 src_lang: str = "en",
                 dst_lang: str = "de",
                 source: str = "manual",
                 used_dict: str = "pons",
                 collections_path: Path = Path("~/.local/share/Anki2/User 1/collection.media")):
        self.original_word = word
        self.original_pos = pos
        self.input_lang = input_lang
        self.src_lang = src_lang
        self.dst_lang = dst_lang
        self.source = source
        self.collections_path = collections_path.expanduser()
        self.manual_selection = manual_selection

        self.entries = entries_factory[used_dict](word, src_lang, dst_lang)()
        self.input_lang = self.get_input_lang(self.input_lang)

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
    def row(self) -> pd.Series:
        df = self.entries
        df = df.loc[df.lang == self.dst_lang]
        if self.original_pos is not None:
            pos = pos_processing(pos=self.original_pos, lang=self.dst_lang,
                                 word=self.original_word)
            df = df.loc[df.pos == pos]
        df["target_len"] = [len(x.split(" ")) for x in df.target]
        # Sometimes first entry for Pons is the whole sentence as a translation
        # instead of simple definition, that's why I'm picking definitions
        # shorter than 4 word.
        # Example: https://de.pons.com/%C3%BCbersetzung/deutsch-englisch/Spiel
        if not df.iloc[:3].loc[df.iloc[:3].target_len <= 3].empty:
            df = df.loc[df.target_len <= 3]
        df.drop(columns=["target_len"], inplace=True)
        return df.iloc[0]

    @property
    def audio(self):
        if self.input_lang == self.src_lang:
            audio = self.row.get("audio_dst")
            word = self.definition
        else:
            audio = self.row.get("audio_src")
            word = self.word
        if audio:
            return get_audio(audio_url=audio,
                             word=word,
                             collections_path=self.collections_path)
        return ""

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
    def gender_src(self):
        return self.row.gender_src

    @property
    def gender_dst(self):
        return self.row.gender_dst

    @property
    def pos_dst(self):
        return self.row.get("pos_dst", "")

    @property
    def tenses_plural(self):
        if forms := self.row.get("forms"):
            return forms
        if flexion := self.row.get("flexion"):
            return flexion

# @property
# def tenses_plural(self):
#     if "verb" in self.pos.lower():
#         return self.__get_tenses()
#     if "noun" in self.pos.lower():
#         return self.__get_plural()
#     return ""

#     
# @property
# def __process_flexicon(self, flexicon):
#     return flexicon_processing(self.original_word,
#                                lang=self.input_lang,
#                                flexicon=flexicon)

# def __get_plural(self):
#     if self.plural:
#         return f"die {self.plural['text'].capitalize()}"
#     else:
#         return self.pons_plural

    @property
    def pos(self):
        if self.original_pos is None:
            return self.row.pos
        return self.original_pos

    def get_input_lang(self, input_lang):
        if input_lang is None:
            return self.row.lang
        return input_lang

    @property
    def word(self):
        word = word_processing(self.original_word, sense=self.row.get("sense", ""))
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

    def get_dict(self):
        if self.input_lang == self.src_lang:
            processed_word = self.definition
        else:
            processed_word = self.word

        row_dict = {
            "processed_word": processed_word,
            "picture": self.image,
            "definition": self.definition,
            "audio": self.audio,
            "example_src": self.example_src,
            "gender_src": self.gender_src,
            "gender_dst": self.gender_dst,
            "tenses_plural": self.tenses_plural,
            "example_dst": self.example_dst,
            "pos": self.pos,
            "pos_dst": self.pos_dst,
            "original_word": self.word,
            "source": self.source
        }
        return row_dict

    def __call__(self):
        return self.get_dict()


if __name__ == "__main__":
    entry = DictEntry("Spiel")()
    print(entry)

    entry = DictEntry("Spiel", used_dict="linguee")()
    print(entry)