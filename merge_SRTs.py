#!/usr/bin/env python3
import os
import pandas as pd
import requests
from zipfile import ZipFile
from io import BytesIO
import pysubs2
from pprint import pprint
from tqdm.auto import tqdm
import datetime
import dotenv
dotenv.load_dotenv()

def get_best_english_sub(imdb_id, out_dir="downloaded_subs"):
    """
    Downloads the best English subtitle for a given IMDB ID using the OpenSubtitles API (v1).
    Returns the local SRT path. Skips download if already present.
    """
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{imdb_id}.srt")

    # ✅ Skip if already downloaded
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path

    api_key = os.environ.get("OPENSUB_API_KEY")
    if not api_key:
        raise RuntimeError("Please set OPENSUB_API_KEY in your environment.")

    headers = {"Api-Key": api_key, "Accept": "application/json", "User-Agent": "wheresthejump/1.0"}
    search_url = "https://api.opensubtitles.com/api/v1/subtitles"
    params = {
        "imdb_id": imdb_id.replace("tt", ""),
        "languages": "en",
        "order_by": "download_count",
        "order_direction": "desc",
        "type": "movie"
    }

    print(f"Searching subtitles for {imdb_id} ...")
    r = requests.get(search_url, headers=headers, params=params)
    r.raise_for_status()
    data = r.json()

    if not data.get("data"):
        raise ValueError(f"No English subtitles found for IMDB {imdb_id}")

    file_id = data["data"][0]["attributes"]["files"][0]["file_id"]

    # Request download link
    download_url = "https://api.opensubtitles.com/api/v1/download"
    d = requests.post(download_url, headers=headers, json={"file_id": file_id})
    d.raise_for_status()
    pprint(d.json())
    if d.json()["remaining"] == 0:
        raise RuntimeError("API quota exceeded.")
    link = d.json()["link"]

    print(f"Downloading subtitles for {imdb_id} ...")
    resp = requests.get(link)
    resp.raise_for_status()

    with open(out_path, "wb") as f:
        f.write(resp.content)

    print(f"Saved: {out_path}")
    return out_path



def merge_subtitles(local_path, downloaded_path, output_path, tolerance_ms=500):
    """
    Merge two SRT subtitle files using pysubs2.
    - Keeps all cues from both files.
    - If a downloaded cue overlaps (±tolerance_ms) with a local cue, combine them.
    - Sorts and saves cleanly.
    """
    local_subs = pysubs2.load(local_path)
    downloaded_subs = pysubs2.load(downloaded_path)

    merged_events = []
    used_dl = [False] * len(downloaded_subs)

    for local_event in local_subs:
        # Find downloaded events that overlap within ±tolerance_ms
        overlaps = []
        for i, dl_event in enumerate(downloaded_subs):
            if used_dl[i]:
                continue
            if (dl_event.end + tolerance_ms >= local_event.start and
                    dl_event.start - tolerance_ms <= local_event.end):
                overlaps.append((i, dl_event))

        if overlaps:
            # Merge overlapping events into one cue
            combined_text = local_event.text.strip()
            for i, dl_event in overlaps:
                combined_text += f"\n\n{dl_event.text.strip()}"
                used_dl[i] = True
            new_event = local_event.copy()
            new_event.text = combined_text
            merged_events.append(new_event)
        else:
            merged_events.append(local_event)

    # Add any unused downloaded events
    for i, dl_event in enumerate(downloaded_subs):
        if not used_dl[i]:
            merged_events.append(dl_event)

    merged_subs = pysubs2.SSAFile()
    merged_subs.events = sorted(merged_events, key=lambda e: e.start)
    merged_subs.save(output_path)
    print(f"[✓] Merged subtitles written to {output_path}")

    return output_path

def process_dataframe(df):
    """
    For each row in df, fetch subs and merge them with the local one.
    Returns a new DataFrame with the merged SRT path.
    """
    merged_paths = []
    for i, row in tqdm(df.iterrows(), total=df.shape[0]):
        imdb_id = row["IMDB"]
        local_srt = row["srt"]

        try:
            downloaded_srt = get_best_english_sub(imdb_id)
            merged_out = os.path.splitext(local_srt)[0] + "_merged.srt"
            merge_subtitles(local_srt, downloaded_srt, merged_out)
            merged_paths.append(merged_out)
        except RuntimeError as e:
            raise
        except Exception as e:
            print(f"Failed for {imdb_id}: {e}")
            merged_paths.append(None)
    df["merged_srt"] = merged_paths
    return df


if __name__ == "__main__":
    df = pd.read_csv("wheresthejump.csv").dropna(subset="SRT Link")
    df["srt"] = df["SRT Link"].apply(lambda url: f"srt/{url.split('/')[-1]}")
    result = process_dataframe(df)
    print(result)
