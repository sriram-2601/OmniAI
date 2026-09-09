"""Leakage-safe temporal and conversation-isolated dataset splitting."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd

from src.common.config import DATA_PROCESSED_DIR, DATA_SAMPLE_DIR, RANDOM_SEED


def parse_twitter_timestamp(ts_str: str) -> datetime:
    """Parse Twitter timestamp format: 'Tue Oct 31 22:10:47 +0000 2017'."""
    try:
        return datetime.strptime(ts_str, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        return datetime.min


def create_leakage_free_splits(
    conversations: List[Dict[str, Any]],
    train_ratio: float = 0.80,
    deduplicate_customer_texts: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split conversations with strict temporal ordering, conversation isolation, and deduplication.

    Guarantees:
    1. Zero conversation ID overlap between splits.
    2. Temporal isolation: All Historical Knowledge Base cases chronologically precede Evaluation cases.
    3. Exact text deduplication across splits: No duplicate customer problem texts across train and eval.

    Args:
        conversations: Reconstructed conversation list.
        train_ratio: Proportion of earlier cases to allocate to the Historical Knowledge Base.
        deduplicate_customer_texts: If True, drop duplicate customer opening texts.

    Returns:
        (knowledge_base_conversations, holdout_eval_conversations)
    """
    print(f"[Split] Processing {len(conversations):,} reconstructed conversations...")

    # 1. Deduplicate by customer problem text if requested
    if deduplicate_customer_texts:
        seen_texts = set()
        deduped = []
        for c in conversations:
            norm_text = c["initial_customer_problem"].lower().strip()
            if norm_text not in seen_texts:
                seen_texts.add(norm_text)
                deduped.append(c)
        print(f"[Split] Deduplicated {len(conversations):,} -> {len(deduped):,} unique customer problem texts.")
        conversations = deduped

    # 2. Chronological sorting for temporal split
    for c in conversations:
        c["_dt"] = parse_twitter_timestamp(c.get("start_time", ""))

    conversations.sort(key=lambda x: x["_dt"])

    # 3. Temporal split point
    split_idx = int(len(conversations) * train_ratio)
    knowledge_base = conversations[:split_idx]
    holdout_eval = conversations[split_idx:]

    # Remove temporary sort key
    for c in conversations:
        c.pop("_dt", None)

    # 4. Strict leakage verification
    kb_ids = {c["conversation_id"] for c in knowledge_base}
    eval_ids = {c["conversation_id"] for c in holdout_eval}
    intersection = kb_ids.intersection(eval_ids)
    assert len(intersection) == 0, f"Critical leakage! Conversation IDs overlap: {len(intersection)}"

    kb_texts = {c["initial_customer_problem"].lower().strip() for c in knowledge_base}
    eval_texts = {c["initial_customer_problem"].lower().strip() for c in holdout_eval}
    text_overlap = kb_texts.intersection(eval_texts)
    assert len(text_overlap) == 0, f"Critical leakage! Problem texts overlap: {len(text_overlap)}"

    print(f"[Split] Split verified leakage-free:")
    print(f"        Historical Knowledge Base (Train): {len(knowledge_base):,} conversations")
    print(f"        Holdout Evaluation Pool (Test):    {len(holdout_eval):,} conversations")
    if knowledge_base and holdout_eval:
        print(f"        KB Time Range:     {knowledge_base[0]['start_time']} -> {knowledge_base[-1]['start_time']}")
        print(f"        Holdout Time Range: {holdout_eval[0]['start_time']} -> {holdout_eval[-1]['start_time']}")

    return knowledge_base, holdout_eval


def save_splits(
    knowledge_base: List[Dict[str, Any]],
    holdout_eval: List[Dict[str, Any]],
    output_dir: Path = DATA_PROCESSED_DIR,
) -> None:
    """Save split datasets to JSONL."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    kb_file = output_dir / "knowledge_base.jsonl"
    eval_file = output_dir / "holdout_pool.jsonl"

    print(f"[Split] Writing {len(knowledge_base):,} cases to {kb_file}...")
    with open(kb_file, "w", encoding="utf-8") as f:
        for item in knowledge_base:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[Split] Writing {len(holdout_eval):,} cases to {eval_file}...")
    with open(eval_file, "w", encoding="utf-8") as f:
        for item in holdout_eval:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print("[Split] Splits saved successfully.")
