import pandas as pd
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from dict_entry import DictEntry


class TooManyRequestsError(Exception):
    pass


class DictCombine(BaseModel):
    dicts: List[DictEntry]
    dict_names: List[str]
    entries: dict = {}
    errors: List[str] = []  # TODO: Should be an Enum
    external_example_dst: str = ""
    external_example_src: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.entries, self.errors = self.get_entries()
        self.validate_external_examples()

    def validate_external_examples(self):
        if self.external_example_dst and not self.external_example_src:
            self.external_example_dst = ""
        if not self.external_example_dst and self.external_example_src:
            self.external_example_src = ""

    @classmethod
    def init(
        cls,
        word: str,
        dicts_to_use: List[str],
        pos: Optional[str] = None,
        input_lang: Optional[str] = None,
        manual_selection: bool = False,
        source: str = "manual",
        src_lang: str = "en",
        dst_lang: str = "de",
        external_example_src: str = "",
        external_example_dst: str = "",
        collections_path: Path = Path("~/.local/share/Anki2/User 1/collection.media")
    ):
        dicts = []
        for dtu in dicts_to_use:
            d = DictEntry(word=word,
                          pos=pos,
                          input_lang=input_lang,
                          manual_selection=manual_selection,
                          src_lang=src_lang,
                          dst_lang=dst_lang,
                          used_dict=dtu,
                          source=source,
                          collections_path=collections_path)
            if d():
                dicts.append(d)
        return cls(dicts=dicts,
                   dict_names=dicts_to_use,
                   external_example_src=external_example_src,
                   external_example_dst=external_example_dst)

    class Config:
        arbitrary_types_allowed = True

    def get_entries(self):
        entries = {}
        errors = []
        for d, n in zip(self.dicts, self.dict_names):
            entries[n], error = d()
            errors.append(error)
        return entries, errors

    def __prepare_df(self, key: str, sort: list = []):
        df = pd.DataFrame()
        kk = [k for k in self.entries.keys()]
        vv = [v.get(key) for v in self.entries.values()]
        df["dictionary"] = kk
        df["value"] = vv
        if sort:
            custom_sort = {x: i for i, x in enumerate(sort)}
            df = df.sort_values(by=["dictionary"], key=lambda x: x.map(custom_sort))
        non_empty_df = df.loc[(~pd.isnull(df.value)) & (df.value != "")]
        if not non_empty_df.empty:
            return non_empty_df
        return df

    def __return_single_value(self, key: str, sort: list = [],
                              examples: list = []):
        df = self.__prepare_df(key, sort)
        return df.iloc[0].value

    def __return_multiple_value(self, key: str, sort: list = [],
                                examples: list = []):
        df = self.__prepare_df(key, sort)
        df = df.loc[(~pd.isnull(df.value)) & (df.value != "")]
        if df.empty:
            return ""
        examples = "<br>".join(df.value.to_list()).split("<br>")
        if len(examples) >= 2:
            return f"1. {examples[0]}<br> 2. {examples[1]}"
        return examples[0]

    @property
    def picture(self):
        return self.__return_single_value("picture")

    @property
    def processed_word(self):
        return self.__return_single_value("processed_word")

    @property
    def definition(self):
        return self.__return_single_value("definition")

    @property
    def audio(self):
        return self.__return_single_value("audio")

    @property
    def example_src(self):
        return self.__return_multiple_value(
            "example_src", sort=["linguee", "pons"],
            examples=[self.external_example_src]
        )

    @property
    def example_dst(self):
        return self.__return_multiple_value(
            "example_dst", sort=["linguee", "pons"],
            examples=[self.external_example_dst]
        )

    @property
    def gender_src(self):
        return self.__return_single_value("gender_src")

    @property
    def gender_dst(self):
        return self.__return_single_value("gender_dst")

    @property
    def tenses_plural(self):
        return self.__return_single_value("tenses_plural")

    @property
    def pos(self):
        return self.__return_single_value("pos")

    @property
    def pos_dst(self):
        return self.__return_single_value("pos_dst")

    @property
    def original_word(self):
        return self.__return_single_value("original_word")

    @property
    def source(self):
        return self.__return_single_value("source")

    @property
    def anki_row(self):
        row_dict = {
            "German": self.processed_word,
            "Picture": self.picture,
            "English": self.definition,
            "Audio": self.audio,
            "Sample sentence": self.example_src,
            "Plural and inflected forms": self.tenses_plural,
            "German Alternatives": "",
            "English Alternatives": self.example_dst,
            "Part of speech": self.pos,
            "original_word": self.original_word,
            "Source": self.source
        }
        return row_dict

    def __call__(self):
        if not self.dicts:
            return {}, self.errors
        if not self.dicts[0]:
            return {}, self.errors
        return self.anki_row, self.errors
