"""CLI script to prepare and process the AppleSupport conversation dataset."""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.reconstruct import reconstruct_brand_conversations
from src.data.split import create_leakage_free_splits, save_splits
from src.data.sample import create_reproducible_sample


def main():
    print("[Pipeline] Step 1: Reconstructing AppleSupport conversations...")
    conversations = reconstruct_brand_conversations(target_brand="AppleSupport")

    # Turn count statistics
    turn_counts = [c["turn_count"] for c in conversations]
    print(f"\n[Pipeline] Conversation Turn Statistics:")
    print(f"           Mean Turns:   {np.mean(turn_counts):.2f}")
    print(f"           Median Turns: {np.median(turn_counts):.1f}")
    print(f"           Min / Max:    {np.min(turn_counts)} / {np.max(turn_counts)}")

    print("\n[Pipeline] Step 2: Creating leakage-free chronological splits...")
    kb, holdout = create_leakage_free_splits(conversations, train_ratio=0.80)
    save_splits(kb, holdout)

    print("\n[Pipeline] Step 3: Generating deterministic benchmark sample (5,000 cases)...")
    create_reproducible_sample(sample_size=5000)

    print("\n[Pipeline] Data preparation complete. Ready for intent discovery and indexing.")


if __name__ == "__main__":
    main()
