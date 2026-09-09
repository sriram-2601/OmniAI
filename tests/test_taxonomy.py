"""Unit tests for IntentTaxonomy and configs/intents.yaml."""
from __future__ import annotations

import pytest
from src.taxonomy.taxonomy import IntentTaxonomy, default_taxonomy


def test_taxonomy_intents_count():
    names = default_taxonomy.get_intent_names()
    assert len(names) == 10, f"Expected 10 intents, got {len(names)}: {names}"


def test_taxonomy_contains_core_intents():
    expected = [
        "BATTERY_POWER",
        "SOFTWARE_UPDATE",
        "ACCOUNT_ACCESS",
        "APP_STORE_BILLING",
        "HARDWARE_DISPLAY",
        "AUDIO_MEDIA",
        "CONNECTIVITY_NETWORK",
        "STORAGE_BACKUP",
        "STORE_REPAIR_SERVICE",
        "OUT_OF_SCOPE",
    ]
    for exp in expected:
        assert default_taxonomy.is_valid_intent(exp), f"Missing intent: {exp}"


def test_intent_metadata_completeness():
    for name in default_taxonomy.get_intent_names():
        info = default_taxonomy.get_intent_info(name)
        assert "name" in info
        assert "description" in info
        assert "positive_examples" in info
        assert len(info["positive_examples"]) >= 2
        assert "inclusion_rules" in info
        assert "exclusion_rules" in info


def test_unknown_intent_raises():
    with pytest.raises(KeyError):
        default_taxonomy.get_intent_info("NON_EXISTENT_INTENT")
