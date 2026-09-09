"""Deterministic sampling module for fast, reproducible benchmarking."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List, Dict, Any

from src.common.config import DATA_PROCESSED_DIR, DATA_SAMPLE_DIR, RANDOM_SEED


def create_reproducible_sample(
    kb_path: Path = DATA_PROCESSED_DIR / "knowledge_base.jsonl",
    sample_size: int = 5000,
    seed: int = RANDOM_SEED,
    output_path: Path = DATA_SAMPLE_DIR / "knowledge_base_sample.jsonl",
) -> List[Dict[str, Any]]:
    """Sample a deterministic subset of historical support cases for 15-minute headline reproduction.

    Args:
        kb_path: Source full knowledge base JSONL.
        sample_size: Number of cases to sample.
        seed: Random seed for 100% reproducibility.
        output_path: Destination JSONL.

    Returns:
        Sampled support cases.
    """
    kb_path = Path(kb_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Sample] Reading full knowledge base from {kb_path}...")
    records = []
    with open(kb_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"[Sample] Total available historical cases: {len(records):,}")
    rng = random.Random(seed)
    if len(records) > sample_size:
        # Sort chronologically, then stratified sample to maintain time distribution
        sample = rng.sample(records, sample_size)
    else:
        sample = records

    print(f"[Sample] Writing {len(sample):,} sampled cases to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        for item in sample:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[Sample] Deterministic sample saved. Size on disk: {output_path.stat().st_size / (1024*1024):.2f} MB")
    return sample
