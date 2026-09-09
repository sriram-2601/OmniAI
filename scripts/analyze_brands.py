"""Deep empirical analysis of candidate brands for brand selection."""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from src.common.config import DATA_RAW_DIR

df = pd.read_parquet(DATA_RAW_DIR / "twcs.parquet")
candidates = ["AppleSupport", "AmazonHelp", "Uber_Support", "SpotifyCares", "Delta"]

print("=" * 80)
print(f"{'Brand':<15} | {'Outbound':<10} | {'Inbound':<10} | {'Has URL %':<10} | {'Mentions DM %':<14} | {'Avg Outbound Chars':<18}")
print("-" * 80)

results = {}
for brand in candidates:
    brand_out = df[df["author_id"] == brand]
    inbound_brand = df[df["text"].str.contains(f"@{brand}", case=False, na=False) & df["inbound"]]
    has_url = float(brand_out["text"].str.contains("http", case=False, na=False).mean() * 100)
    has_dm = float(brand_out["text"].str.contains(r"\bDM\b", regex=True, na=False).mean() * 100)
    avg_chars = float(brand_out["text"].str.len().mean())
    
    results[brand] = {
        "outbound": len(brand_out),
        "inbound": len(inbound_brand),
        "has_url": has_url,
        "has_dm": has_dm,
        "avg_chars": avg_chars,
    }
    print(f"{brand:<15} | {len(brand_out):<10,d} | {len(inbound_brand):<10,d} | {has_url:<10.1f} | {has_dm:<14.1f} | {avg_chars:<18.1f}")

print("=" * 80)

# Sample 3 representative resolutions for top candidates
print("\n--- SAMPLE RESOLUTIONS ---")
for brand in ["AppleSupport", "AmazonHelp", "SpotifyCares"]:
    print(f"\n[{brand} Samples]")
    samples = df[(df["author_id"] == brand) & (df["text"].str.len() > 100)]["text"].head(3).tolist()
    for i, s in enumerate(samples, 1):
        print(f"  {i}. {s}")
