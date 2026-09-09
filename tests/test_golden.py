"""Unit tests for Golden Evaluation Benchmark Set."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.common.config import DATA_GOLDEN_DIR
from src.taxonomy.taxonomy import default_taxonomy
from src.common.schemas import GoldenExample


def test_golden_set_file_exists():
    path = DATA_GOLDEN_DIR / "golden_set.jsonl"
    assert path.exists(), f"Missing {path}"
    assert path.stat().st_size > 5000


def test_golden_set_size_and_schema():
    path = DATA_GOLDEN_DIR / "golden_set.jsonl"
    examples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                example = GoldenExample(**data)
                examples.append(example)

    assert len(examples) == 200, f"Expected 200 examples, got {len(examples)}"

    # Check intent validity
    for ex in examples:
        assert default_taxonomy.is_valid_intent(ex.intent), f"Invalid intent: {ex.intent}"
        assert ex.expected_action in ("AUTO_HANDLE", "ESCALATE")
        assert ex.risk_level in ("LOW", "MEDIUM", "HIGH")
        assert len(ex.customer_message) >= 5
        assert len(ex.escalation_reason) >= 5


def test_golden_set_balanced_intents():
    path = DATA_GOLDEN_DIR / "golden_set.jsonl"
    from collections import Counter
    counts = Counter()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            counts[json.loads(line)["intent"]] += 1

    assert len(counts) == 10, f"Expected 10 intents, got {len(counts)}"
    for intent, count in counts.items():
        assert count == 20, f"Expected 20 per intent, got {count} for {intent}"
