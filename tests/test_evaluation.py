"""Unit tests for evaluation metrics, judge scoring, human calibration, and failure analysis."""
from __future__ import annotations

import pytest
from src.evaluation.escalation import compute_escalation_metrics
from src.evaluation.calibration import compute_judge_human_agreement
from src.evaluation.judge import default_judge
from src.evaluation.failure_analysis import analyze_failures
from src.common.schemas import EvidenceItem


def test_escalation_metrics_computation():
    expected = ["AUTO_HANDLE", "AUTO_HANDLE", "ESCALATE", "ESCALATE"]
    actual = ["AUTO_HANDLE", "ESCALATE", "ESCALATE", "AUTO_HANDLE"]
    risks = ["LOW", "LOW", "HIGH", "HIGH"]

    metrics = compute_escalation_metrics(expected, actual, risks)

    assert metrics["total_evaluated"] == 4
    assert metrics["auto_handled_count"] == 2
    assert metrics["escalated_count"] == 2
    assert metrics["coverage_percentage"] == 50.0
    # 1 safe auto out of 2 total autos
    assert metrics["auto_handling_precision"] == 0.5
    # 1 dangerous auto (HIGH risk marked AUTO_HANDLE)
    assert metrics["dangerous_auto_count"] == 1
    assert metrics["false_auto_handling_rate"] == 0.25


def test_judge_reply_heuristic_fallback():
    msg = "My iPhone 6s battery is draining very fast."
    draft = "We're here to help. You can check battery health under Settings > Battery. Learn more: [URL]"
    evidence = [
        EvidenceItem(
            case_id="123",
            customer_message="battery drains fast",
            brand_response="Check settings > battery [URL]",
            similarity_score=0.75,
            intent_match=True,
            resolution_match=True,
        )
    ]

    res = default_judge.judge_reply(
        customer_message=msg,
        draft_reply=draft,
        intent="BATTERY_POWER",
        decision="AUTO_HANDLE",
        evidence=evidence,
    )

    assert "overall" in res
    assert "correctness" in res
    assert "historical_grounding" in res
    assert "helpfulness" in res
    assert "safety" in res
    assert "brand_fit" in res
    assert res["overall"] >= 3.5
    assert res["safety"] == 5.0


def test_judge_human_calibration():
    human = [4.5, 4.0, 3.5, 2.0, 1.5]
    llm = [4.6, 4.1, 3.4, 2.2, 1.8]

    metrics = compute_judge_human_agreement(human, llm)

    assert metrics["sample_size"] == 5
    assert metrics["spearman_correlation"] > 0.8
    assert metrics["pearson_correlation"] > 0.8
    assert metrics["mean_absolute_error"] < 0.5
    assert metrics["near_agreement_pct_within_half_point"] == 100.0


def test_failure_analysis():
    records = [
        {
            "id": "gold_test_01",
            "customer_message": "My iOS update broke wifi and drained battery",
            "expected_intent": "BATTERY_POWER",
            "predicted_intent": "SOFTWARE_UPDATE",
            "expected_action": "AUTO_HANDLE",
            "actual_decision": "ESCALATE",
            "judge_overall": 4.5,
        },
        {
            "id": "gold_test_02",
            "customer_message": "Logged into my account and need to change my wallpaper",
            "expected_intent": "HARDWARE_DISPLAY",
            "predicted_intent": "HARDWARE_DISPLAY",
            "expected_action": "AUTO_HANDLE",
            "actual_decision": "ESCALATE",
            "judge_overall": 4.5,
        }
    ]

    report = analyze_failures(records)

    assert report["total_failures_detected"] >= 1
    assert len(report["top_failure_modes"]) == 5
