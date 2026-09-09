"""Download and acquire the Customer Support on Twitter dataset.

The Kaggle dataset thoughtvector/customer-support-on-twitter is hosted in exact
unmodified form (2.81M rows, 492MB CSV) on Hugging Face at SunidhiSriram/twcs.
This module acquires the raw dataset and converts it to high-performance parquet
at data/raw/twcs.parquet for ultra-fast, reproducible loading.
"""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path
import pandas as pd
from tqdm import tqdm

from src.common.config import DATA_RAW_DIR

RAW_CSV_NAME = "twcs.csv"
RAW_PARQUET_NAME = "twcs.parquet"
RAW_CSV_PATH = DATA_RAW_DIR / RAW_CSV_NAME
RAW_PARQUET_PATH = DATA_RAW_DIR / RAW_PARQUET_NAME

HF_TWCS_CSV_URL = (
    "https://huggingface.co/datasets/SunidhiSriram/twcs/resolve/main/twcs.csv"
)


def acquire_dataset(force: bool = False) -> Path:
    """Download the authentic twcs.csv and convert to optimized parquet.

    Returns:
        Path to the high-performance parquet file.
    """
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    if RAW_PARQUET_PATH.exists() and not force:
        size_mb = RAW_PARQUET_PATH.stat().st_size / (1024 * 1024)
        if size_mb > 50:
            print(f"[Dataset] Found existing parquet dataset at {RAW_PARQUET_PATH} ({size_mb:.2f} MB). Ready.")
            return RAW_PARQUET_PATH

    # Check if raw CSV exists
    if not RAW_CSV_PATH.exists() or force:
        print(f"[Dataset] Downloading authentic Kaggle twcs.csv from mirror:")
        print(f"          URL: {HF_TWCS_CSV_URL}")
        print(f"          Destination: {RAW_CSV_PATH}")

        headers = {"User-Agent": "Hiver-Support-Agent-Auditor/1.0"}
        req = urllib.request.Request(HF_TWCS_CSV_URL, headers=headers)

        with urllib.request.urlopen(req) as response:
            total_size = int(response.info().get("Content-Length", 0))
            with open(RAW_CSV_PATH, "wb") as f_out, tqdm(
                desc="twcs.csv",
                total=total_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                chunk_size = 2 * 1024 * 1024  # 2MB chunks
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    bar.update(len(chunk))

        size_mb = RAW_CSV_PATH.stat().st_size / (1024 * 1024)
        print(f"[Dataset] Download complete: {size_mb:.2f} MB")

    # Convert to compressed Parquet for 10x faster loads and smaller footprint
    print(f"[Dataset] Converting twcs.csv to optimized Parquet format...")
    # Specify schema dtypes for robust parsing
    dtypes = {
        "tweet_id": "str",
        "author_id": "str",
        "inbound": "bool",
        "created_at": "str",
        "text": "str",
        "response_tweet_id": "str",
        "in_response_to_tweet_id": "str",
    }
    df = pd.read_csv(RAW_CSV_PATH, dtype=dtypes, low_memory=False)
    print(f"[Dataset] Parsed {len(df):,} rows. Writing to {RAW_PARQUET_PATH} with snappy compression...")
    df.to_parquet(RAW_PARQUET_PATH, compression="snappy", index=False)
    parquet_size_mb = RAW_PARQUET_PATH.stat().st_size / (1024 * 1024)
    print(f"[Dataset] Saved compressed parquet: {parquet_size_mb:.2f} MB")

    # Optionally clean up raw CSV to save disk space
    if RAW_CSV_PATH.exists():
        RAW_CSV_PATH.unlink()
        print(f"[Dataset] Cleaned up temporary CSV {RAW_CSV_PATH} to maintain compact workspace.")

    return RAW_PARQUET_PATH


if __name__ == "__main__":
    acquire_dataset()
