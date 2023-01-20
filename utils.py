import errno
import os
import signal
import functools
import re
from typing import List
import requests
import shutil
from pathlib import Path


from simple_image_download import simple_image_download as simp
response = simp.simple_image_download


class TimeoutError(Exception):
    pass

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wrapper

    return decorator


@timeout(15)
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
    "en": en_noun_processing,
    "de": de_noun_processing,
}


def noun_processing(noun: str, lang: str, gender: str):
    return noun_processors[lang](noun, gender=gender)


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


def en_flexicon_processing(flexicon: str, **kwargs):
    return flexicon


def de_flexicon_processing(flexicon: str, **kwargs):
    word = kwargs["word"]
    word = word.capitalize() + flexicon.split("-")[-1].split(">")[0]
    return f"die {word}"


flexicon_processor = {
    "en": en_flexicon_processing,
    "de": de_flexicon_processing,
}


def flexicon_processing(flexicon: str, lang: str, word: str):
    return flexicon_processor[lang](flexicon, word=word)


def get_audio(audio_url, word, collections_path):
    r = requests.get(audio_url)
    audio_name = f"{word}.mp3"
    audio_save = f"audio/{word}.mp3"
    open(audio_save, "wb").write(r.content)
    shutil.copy(audio_save, collections_path / audio_name)
    return f"[sound:{audio_name}]"


del_italics = lambda x: x.replace("{it}", "").replace("{/it}", "")

def get_sub(audio: str):
    if "gg" in audio[:2]:
        return "gg"
    if "bix" in audio[:3]:
        return "bix"
    m = re.search(r"[0-9]", audio[0])
    if m:
        return "number"
    return audio[0]

def get_webster_audio(webster_entries: List[dict], audio_base_url: str):
    try:
        audio = webster_entries[0]["hwi"]["prs"][0]["sound"]["audio"]
    except KeyError:
        return ""
    else:
        audio_save = f"audio/{audio}.mp3"
        audio_url = audio_base_url.format(subdirectory=get_sub(audio), base_filename=audio)
        return audio_url

