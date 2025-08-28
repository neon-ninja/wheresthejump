#!/usr/bin/env python3

from tqdm.auto import tqdm
import os
import undetected_chromedriver as uc
driver = uc.Chrome(headless=False, use_subprocess=False)
driver.implicitly_wait(10)
driver.set_page_load_timeout(15)
from selenium.webdriver.common.by import By
import time
import pandas as pd
pd.set_option("display.max_colwidth", None)

df = pd.read_html("https://wheresthejump.com/full-movie-list/")[0]
df["URL"] = pd.read_html("https://wheresthejump.com/full-movie-list/", extract_links="all")[0].iloc[:,0].str[1]

rows = []

for i, row in tqdm(df.iterrows(), total=df.shape[0]):
    row = row.to_dict()
    try:
        driver.get(row["URL"])
    except Exception as e:
        print(e)
    for _ in range(30):
        print(driver.current_url)
        if driver.current_url != row["URL"]:
            driver.get(url)
        print(driver.title)
        if driver.title == "One moment, please...":
            time.sleep(1)
        else:
            break
    try:
        imdb = driver.find_element(By.CSS_SELECTOR, "a[href*=imdb]").get_attribute("href").replace('https://www.imdb.com/title/', "").strip("/#")
        summary = driver.find_element(By.CSS_SELECTOR, "div.video-info-grid-column>p").text
        rating = driver.find_element(By.CSS_SELECTOR, "div.entry-content>p:has(strong)").text.replace("Jump Scare Rating: ", "")
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(e)
        rows.append(row)
        continue
    try:
        srt_link = driver.find_element(By.CSS_SELECTOR, "a[href*=srt]").get_attribute("href")
    except:
        srt_link = ""
    row.update({
        "IMDB": imdb,
        "Summary": summary,
        "Rating": rating,
        "SRT Link": srt_link
    })
    print(row)
    rows.append(row)
    if i % 50 == 0:
        pd.DataFrame(rows).to_csv("wheresthejump.csv", index=False)
    if srt_link:
        os.makedirs("srt", exist_ok=True)
        url = srt_link
        driver.get(url)
        for _ in range(30):
            print(driver.current_url)
            if driver.current_url != url:
                driver.get(url)
            if driver.title == "One moment, please...":
                time.sleep(1)
            else:
                break
        with open(f"srt/{srt_link.split('/')[-1]}", "wb") as f:
            f.write(driver.find_element(By.TAG_NAME, "pre").text.encode("utf-8"))

pd.DataFrame(rows).to_csv("wheresthejump.csv", index=False)