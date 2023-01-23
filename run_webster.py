from typing import List
import pandas as pd
from bs4 import BeautifulSoup
import time
from copy import copy
import argparse

from selenium import webdriver
from dict_entry import TwoEntries


def get_words(soup: List[BeautifulSoup]):
    words = []
    for s in soup:
        a = s.find("a")
        if "..." in a.text:
            word = a.get("href").split("/")[-1].replace("%20", " ")
        else:
            word = a.text
        words.append(word)
    return words


def process_words(driver):
    new_words = []
    soup = BeautifulSoup(driver.page_source)
#     import pdb; pdb.set_trace()
    saved_words_soup = soup.find_all("li", {"class": "words-list-item item-even"})
#     saved_words += [x.find("a").text for x in saved_words_soup]
    new_words += get_words(saved_words_soup)
    saved_words_soup = soup.find_all("li", {"class": "words-list-item item-odd"})
#     saved_words += [x.find("a").text for x in saved_words_soup]
    new_words += get_words(saved_words_soup)
    return new_words


def get_saved_words(driver, df):
    driver.get("https://www.merriam-webster.com/saved-words")
    time.sleep(10)
    saved_words = []
    soup = BeautifulSoup(driver.page_source)
    page_num = soup.find("ul", {"class": "ul-paginator"}).text.strip()
    _, num_of = [int(x) for x in page_num.split(" of ")]

    for page in range(1, num_of + 1):
        print(f"Page: {page}")
        driver.get(f"https://www.merriam-webster.com/saved-words?page={page}")
        time.sleep(5)
        old_words = copy(saved_words)
        new_words = process_words(driver=driver)
        saved_words += new_words
        if len(old_words) == len(saved_words) and page != num_of:
            driver.get(f"https://www.merriam-webster.com/saved-words?page={page}")
            time.sleep(10)
            new_words = process_words(driver=driver)
            saved_words += new_words

        print(len(saved_words))
        all_saved = [w in df.saved_words.to_list() for w in new_words]
        import pdb; pdb.set_trace()
        if all(all_saved):
            return saved_words
        # for w in saved_words:
        #     if w in df.saved_words.to_list():
    return saved_words


def run_scraper():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--window-size=1366,768")
    chrome_options.add_experimental_option('prefs', {'intl.accept_languages': 'en,en_US'})
    driver = webdriver.Chrome(chrome_options=chrome_options)
    driver.get("https://www.merriam-webster.com/login")
    input("Logged in?")

    try:
        df = pd.read_csv("webster_saved_words.csv")
    except FileNotFoundError:
        df = pd.DataFrame(columns=["saved_words"])
    saved_words = get_saved_words(driver, df)
    new_df = pd.DataFrame()
    new_df["saved_words"] = list(set(df.saved_words.to_list() + saved_words))
    new_df.to_csv("webster_saved_words.csv", index=None)


def process_entry(entry: dict):
    new_entry = {
        "Word": entry["processed_word"],
        "Picture": entry["picture"],
        "Definition": entry["definition"],
        "Audio": entry["audio"],
        "Part of speech": entry["pos"],
        "Sample sentence": entry["example_src"],
        "Original word": entry["original_word"]
    }
    return new_entry

        
def run_definitions():
    df = pd.read_csv("webster_saved_words.csv")
    try:
        webster_df = pd.read_csv(
            "webster.csv",
            index_col=False,
            header=None,
            names=["Word", "Picture", "Definition", "Audio",
                   "Part of speech", "Sample sentence", "Original word"]
        )
    except FileNotFoundError:
        webster_df = pd.DataFrame(
            columns=["Word", "Picture", "Definition", "Audio",
                     "Part of speech", "Sample sentence", "Original word"]
        )
    entries = webster_df.to_dict("records")
    for ix, row in df.iterrows():
        print(ix)
        word = row.saved_words
        if word in webster_df["Original word"].to_list():
            continue
        print(word)
        ee, _ = TwoEntries.webster(word)()
        if ee[0]:
            ee = [process_entry(x) for x in ee]
            entries.extend(ee)
        if ix % 10 == 1:
            webster_df = pd.DataFrame(entries)
            webster_df = webster_df.sample(frac=1).reset_index(drop=True)
            webster_df.to_csv("webster.csv", index=None, header=None)
    webster_df = pd.DataFrame(entries)

    webster_df = webster_df.sample(frac=1).reset_index(drop=True)
    webster_df.to_csv("webster.csv", index=None, header=None)


def run(scrape=False):
    if scrape:
        run_scraper()
    run_definitions()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--scrape", action="store_true")
    args = parser.parse_args()
    run(args.scrape)


    
