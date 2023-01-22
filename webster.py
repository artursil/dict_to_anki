import re
import requests
import json
import pandas as pd
from collections import defaultdict
from dict_secrets import WEBSTER, THESAURUS
from utils import del_italics, en_verb_processing, get_webster_audio

class WebsterEntries():
    def __init__(self, word: str, *args, **kwargs):
        self.original_word = word
        self.webster_url = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={key}"
        self.thesaurus_url = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{word}?key={key}"
        self.audio_base = "https://media.merriam-webster.com/audio/prons/en/us/mp3/{subdirectory}/{base_filename}.mp3"
        self.webster, self.thesarus = self.get_entries()

    def get_entries(self):
        word_url = self.webster_url.format(word=self.original_word.replace(" ", "%20"),
                                           key=WEBSTER)
        webster_entries = json.loads(requests.get(word_url).text)
        word_url = self.thesaurus_url.format(word=self.original_word.replace(" ", "%20"),
                                             key=THESAURUS)
        thesaurus_entries = json.loads(requests.get(word_url).text)
        return webster_entries, thesaurus_entries


    def process_desc(self, desc):
        pattern = re.compile(r"{dx_def}.+{/dx_def}")
        if m := pattern.search(desc):
            desc = desc.replace(m[0], "")
        replace_d = {
            "{wi}": "<i>",
            "{/wi}": "</i>",
            "{it}": "<i>",
            "{/it}": "</i>",
            "{bc}": "",
        }
        for k, v in replace_d.items():
            desc = desc.replace(k, v)
        return desc

        

    def process_webster_entries(self, thesaurus_entries: list, webster_entries: list,
                                definitions: list = []):
        definitions = []
        # audio = get_webster_audio(webster_entries)
        if not thesaurus_entries and isinstance(webster_entries[0], str):
            return definitions
        elif not thesaurus_entries:
            thesaurus_entries = [""]
        audio = ""
        if isinstance(thesaurus_entries[0], str):
            entries = webster_entries
            synonyms = thesaurus_entries
        else:
            entries = thesaurus_entries
            synonyms = []
        audio = ""
        if isinstance(webster_entries[0], dict):
            audio = get_webster_audio(webster_entries, self.audio_base)
        else:
            audio = ""

            if isinstance(thesaurus_entries[0], str):
                return definitions
        for entry in entries:
            fl = entry["fl"]

            for d in entry["def"][0]["sseq"]:
                dt = d[0][1]
                if sense := dt.get("sense"):
                    dt = sense["dt"]
                else:
                    dt = dt["dt"]
                desc = dt[0][-1]
                try:
                    example = f"<i> {dt[1][-1][0]['t'].replace(self.original_word, '_____')}</i>"
                except (IndexError, KeyError, TypeError):
                    example = ""
                else:
                    example = f"<b>Example:</b><br> {del_italics(example)}"
                if synonyms:
                    syn_list = synonyms[:5]
                else:
                    try:
                        syns = d[0][1]["syn_list"][0]
                    except KeyError:
                        try:
                            syns = d[0][-1]["sim_list"][0]
                        except KeyError:
                            syns = []
                    syn_list = "<b>Synonyms: </b><br>" +", ".join([x["wd"] for x in syns][:5])
                desc = f"{desc}<br><br>{example}<br><br>{syn_list}"
                word = self.original_word
                if fl == "verb":
                    word = en_verb_processing(word)
                desc = self.process_desc(desc)
                definition = {
                    "processed_word": f"{word} ({fl})",
                    "pos": fl,
                    "target": desc,
                    "synonyms": syn_list,
                    "audio_src": audio,
                    "audio_dst": audio,
                    "lang": "en",
                }
                definitions.append(definition)
        return definitions

    def get_df(self):
        definitions = self.process_webster_entries(
            thesaurus_entries=self.thesarus, webster_entries=self.webster
        )
        df = pd.DataFrame(definitions)
        return df

    def __call__(self):
        return self.get_df()


if __name__ == "__main__":
    entries = WebsterEntries("imperative")
    df = entries()
