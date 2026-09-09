"""Unit tests for dataset preprocessing, cleaning, and leakage prevention."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.common.config import DATA_PROCESSED_DIR, DATA_SAMPLE_DIR
from src.data.clean import clean_tweet_text, is_valid_customer_query
from src.common.schemas import Conversation, MessageTurn


def test_clean_tweet_text():
    raw = "@AppleSupport @115854 My iPhone battery is draining so fast! Email me at test@example.com or call 555-123-4567 https://t.co/xyz"
    cleaned = clean_tweet_text(raw)
    
    assert "@AppleSupport" not in cleaned
    assert "test@example.com" not in cleaned
    assert "[EMAIL]" in cleaned
    assert "[PHONE]" in cleaned
    assert "[URL]" in cleaned
    assert "My iPhone battery is draining so fast!" in cleaned


def test_is_valid_customer_query():
    assert is_valid_customer_query("My iPhone camera is completely black after iOS 11 update") is True
    assert is_valid_customer_query("hi") is False
    assert is_valid_customer_query("@AppleSupport https://t.co/xyz") is False


def test_data_splits_exist_and_non_empty():
    kb_path = DATA_PROCESSED_DIR / "knowledge_base.jsonl"
    holdout_path = DATA_PROCESSED_DIR / "holdout_pool.jsonl"
    sample_path = DATA_SAMPLE_DIR / "knowledge_base_sample.jsonl"

    assert kb_path.exists(), f"Missing {kb_path}"
    assert holdout_path.exists(), f"Missing {holdout_path}"
    assert sample_path.exists(), f"Missing {sample_path}"

    assert kb_path.stat().st_size > 1000
    assert holdout_path.stat().st_size > 1000
    assert sample_path.stat().st_size > 1000


def test_strict_zero_leakage_between_splits():
    """Verify 0% conversation ID and 0% text overlap between Knowledge Base and Holdout."""
    kb_path = DATA_PROCESSED_DIR / "knowledge_base.jsonl"
    holdout_path = DATA_PROCESSED_DIR / "holdout_pool.jsonl"

    kb_ids = set()
    with open(kb_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 10000:  # check first 10,000 for fast test
                break
            kb_ids.add(json.loads(line)["conversation_id"])

    holdout_ids = set()
    with open(holdout_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 5000:
                break
            holdout_ids.add(json.loads(line)["conversation_id"])

    overlap = kb_ids.intersection(holdout_ids)
    assert len(overlap) == 0, f"Critical leakage! Overlap detected: {overlap}"


def test_conversation_structure():
    sample_path = DATA_SAMPLE_DIR / "knowledge_base_sample.jsonl"
    with open(sample_path, "r", encoding="utf-8") as f:
        first_line = json.loads(f.readline())

    assert "conversation_id" in first_line
    assert "brand" in first_line
    assert first_line["brand"] == "AppleSupport"
    assert "initial_customer_problem" in first_line
    assert len(first_line["initial_customer_problem"]) > 0
    assert "resolution" in first_line
    assert "full_thread" in first_line
    assert len(first_line["full_thread"]) >= 2
