class LangReactorEntry():
    def __init__(self, row: pd.Series,
                 collections_path=Path("/home/artursil/.local/share/Anki2/User 1/collection.media")):       
        self.row = row
        self.word = row.word
        self.lemma = row.lemma
#         self.definition = row.definition
        self.subtitle = row.subtitle
        self.translation = row.translation
        self.pos = row.part_of_speech
        self.lin_entries = get_lin_entries(self.lemma)
        self.pons_entries = get_ponsentries(self.lemma)
        self.collections_path = collections_path

    @property
    def definition(self):
        if pd.isnull(self.row.definition):
            spcial_char_map = {ord('ä'):'ae', ord('ü'):'ue', ord('ö'):'oe', ord('ß'):'ss'}
            definition = self.lemma.translate(spcial_char_map)
            print(definition)
            return definition
        return self.row.definition
        
        
    def __process_entries(self):
        ple = process_len_entry(l_entries=self.lin_entries, 
                                word=self.word, 
                                lemma=self.lemma, 
                                part_of_speech=self.pos)
        
        self.processed_entries, self.plural, self.pos = ple
        
    @property
    def tenses_plural(self):
        if self.pos.lower() == "verb":
            return self.__get_tenses()
        if self.pos.lower() == "noun":
            return self.__get_plural()
        return ""
    
    def __get_tenses(self):
        
        head = self.pons_entries[0]["roms"][0]["headword_full"]
        soup = BeautifulSoup(head)
#         import pdb; pdb.set_trace()
        return soup.find("span").get("title")
    
    @property
    def pons_plural(self):
        if not self.pons_entries:
            return ""
        head = self.pons_entries[0]["roms"][0]["headword_full"]
        soup = BeautifulSoup(head)
        
        if flexicon := soup.find("span", {"class": "flexion"}):
            text = flexicon.text
        else:
            text = ""
        word = self.lemma.capitalize() + text.split("-")[-1].split(">")[0]
#         import pdb; pdb.set_trace()
        return f"die {word}"
    
    def __get_plural(self):
        if self.plural:
            return f"die {self.plural['text'].capitalize()}"
        else:
            return self.pons_plural
    
    @property
    def example_src(self):
        src, _ = get_examples(self.processed_entries, 
                              self.definition)
        if src:
            return f"1. {self.subtitle}<br> 2. {src}"
        else:
            return self.subtitle
    
    @property
    def example_translation(self):
        _, dst = get_examples(self.processed_entries, 
                              self.definition)
        if dst:
            return f"1. {self.translation}<br> 2. {dst}"
        else:
            return self.translation
    
    @property
    def processed_word(self):
        if self.pos.lower() != "noun":
            return self.lemma
        elif not self.processed_entries:
            return self.lemma.capitalize()
        ddd = self.processed_entries[0]["pos"].split(",")[-1].strip()
        return f"{DER_DIE_DAS[ddd]} {self.lemma.capitalize()}"
    
    @property
    def get_image(self):
        image_path = downloadimages(self.definition)
        img_name = image_path.parent.stem + image_path.suffix
        img_dst = self.collections_path / img_name
        shutil.copy(image_path, img_dst)
        return f"<img src='{img_name}'>"

    
    def process_row(self):
        self.__process_entries()
        self.pons_entries = process_pons_entries(self.pons_entries,
                                                 self.pos.lower())
        audio_save = get_len_audio(self.processed_entries, self.word, self.collections_path)
        row_dict = {
            "German": self.processed_word,
            "Picture": self.get_image,
            "English": self.definition,
            "Audio": audio_save,
            "Sample sentence": self.example_src,
            "Plural and inflected forms": self.tenses_plural,
            "German Alternatives": "",
            "English Alternatives": self.example_translation,
            "Part of speech": self.pos,
            "original_word": self.word,
            "Source": "Language Reactor"
        }
        return row_dict
    
    def __call__(self):
        if self.lin_entries == {'message': 'The Linguee server returned 503'}:
            return "503 Error"
        return self.process_row()
