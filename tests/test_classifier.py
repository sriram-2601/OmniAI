"""Unit tests for Intent Classifiers (Baselines and Main Semantic Classifier)."""
from __future__ import annotations

import pytest
from src.classifier.baseline import MajorityClassBaseline, TfidfLogisticBaseline
from src.classifier.classifier import default_classifier
from src.taxonomy.taxonomy import default_taxonomy


def test_majority_baseline_prediction():
    model = MajorityClassBaseline(majority_intent="BATTERY_POWER")
    preds = model.predict(["my phone is slow", "my battery dies"])
    assert preds == ["BATTERY_POWER", "BATTERY_POWER"]

    pred_one = model.predict_one("hello")
    assert pred_one.intent == "BATTERY_POWER"
    assert pred_one.confidence == 0.10


def test_semantic_classifier_predict_one():
    # Test high-affinity clear inputs
    pred_battery = default_classifier.predict_one("My iPhone battery is draining from 100 to 0 in 1 hour.")
    assert pred_battery.intent == "BATTERY_POWER"
    assert pred_battery.confidence > 0.30

    pred_id = default_classifier.predict_one("My Apple ID is locked for security reasons and I can't receive my 2FA code.")
    assert pred_id.intent == "ACCOUNT_ACCESS"
    assert pred_id.confidence > 0.30

    pred_bill = default_classifier.predict_one("Why was my credit card charged $14.99 for an iTunes subscription?")
    assert pred_bill.intent == "APP_STORE_BILLING"
    assert pred_bill.confidence > 0.30


def test_semantic_classifier_empty_input():
    pred_empty = default_classifier.predict_one("")
    assert pred_empty.intent == "OUT_OF_SCOPE"
    assert pred_empty.confidence == 0.0


def test_semantic_classifier_batch():
    queries = [
        "iPhone battery dying instantly",
        "Wi-Fi toggle greyed out on iOS 11",
        "How do I cancel my Apple Music trial?",
    ]
    preds = default_classifier.predict_batch(queries)
    assert len(preds) == 3
    for p in preds:
        assert default_taxonomy.is_valid_intent(p.intent)
        assert 0.0 <= p.confidence <= 1.0
