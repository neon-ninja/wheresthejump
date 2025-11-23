#!/usr/bin/env python3

from tqdm.auto import tqdm
import os
import requests_html
import time
import pandas as pd
import re
pd.set_option("display.max_colwidth", None)

s = requests_html.HTMLSession()

df = pd.read_csv("wheresthejump.csv")
missing = df[df["SRT Link"].isna() & (df["Jump Count"] > 0)]
missing["SRT Link"] = missing["Movie Name"].apply(lambda name: f"{name}.srt")
df.update(missing)
df.to_csv("wheresthejump.csv", index=False)
missing = df[~df["SRT Link"].str.contains("wheresthejump.com", na=False) & (df["Jump Count"] > 0)]
missing = missing.loc[~missing["SRT Link"].apply(lambda f: os.path.isfile(f"srt/{f}"))]
print(missing)

for i, row in tqdm(missing.iterrows(), total=missing.shape[0]):
    row = row.to_dict()
    html = s.get(row["URL"]).html
    with open(f"srt/{row['Movie Name']}.srt", "w") as f:
        index = 1
        for p in html.find("p"):
            time = re.search(r"\d{2}:\d{2}:\d{2}", p.text)
            if time:
                end_time = pd.Timedelta(time.group(0))
                start_time = end_time - pd.Timedelta("00:00:05")
                start_time = str(start_time).replace("0 days ", "")
                end_time = str(end_time).replace("0 days ", "")
                major = len(p.find("strong")) > 0
                if major:
                    text = "Upcoming jump scare (Major)"
                else:
                    text = "Upcoming jump scare (Minor)"
                f.write(f"{index}\n{start_time},000 --> {end_time},000\n{text}\n\n")
                index += 1

