import shutil
from typing import Optional
from pathlib import Path
from abc import ABC, abstractmethod
from utils import downloadimages

class DictBase(ABC):
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

