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
