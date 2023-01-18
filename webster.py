import requests
import json
import pandas as pd
from collections import defaultdict
from dict_secrets import WEBSTER, THESAURUS
from utils import del_italics, get_webster_audio

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

    def process_webster_entries(self, thesaurus_entries: list, webster_entries: list,
                                definitions: list = []):
        definitions = []
        # audio = get_webster_audio(webster_entries)
        audio = ""
        if isinstance(thesaurus_entries[0], str):
            entries = webster_entries
            synonyms = thesaurus_entries
        else:
            entries = thesaurus_entries
            synonyms = []
        audio = get_webster_audio(webster_entries, self.audio_base)
        for entry in entries:
            fl = entry["fl"]

            for d in entry["def"][0]["sseq"][:2]:
                dt = d[0][1]["dt"]
                desc = dt[0][-1]
                try:
                    example = f"<i>// {dt[1][-1][0]['t'].replace(self.original_word, '_____')}</i>"
                    example = f"Example: {del_italics(example)}"
                except IndexError:
                    example = ""
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
                desc = f"{desc}<br>{example}<br>{syn_list}"
                definition = {
                    "processed_word": f"{self.original_word} ({fl})",
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
