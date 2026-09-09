"""Unit tests for RiskClassifier and OperationalRouter safety policies."""
from __future__ import annotations

import pytest
from src.routing.risk import default_risk_classifier
from src.routing.router import default_router
from src.common.schemas import IntentPrediction, RiskAssessment, EvidenceItem


def test_high_risk_financial_override():
    msg = "I see an unauthorized charge of $49.99 on my credit card from Apple."
    risk = default_risk_classifier.evaluate_risk(msg, "APP_STORE_BILLING", 0.90)

    assert risk.level == "HIGH"
    assert risk.requires_human_verification is True
    assert any("financial" in f.lower() or "billing" in f.lower() for f in risk.risk_factors)


def test_high_risk_security_override():
    msg = "My Apple ID was hacked and someone changed my trusted phone number."
    risk = default_risk_classifier.evaluate_risk(msg, "ACCOUNT_ACCESS", 0.85)

    assert risk.level == "HIGH"
    assert risk.requires_human_verification is True


def test_safety_hazard_battery_smoke():
    msg = "My phone battery is swollen and smoke is coming out."
    risk = default_risk_classifier.evaluate_risk(msg, "BATTERY_POWER", 0.95)

    assert risk.level == "HIGH"
    assert risk.score >= 0.95


def test_router_escalates_on_high_risk():
    intent = IntentPrediction(intent="APP_STORE_BILLING", confidence=0.95, reason="")
    risk = RiskAssessment(level="HIGH", score=0.90, risk_factors=["Unauthorized charge"])
    evidence = [
        EvidenceItem(case_id="c1", customer_message="billing", brand_response="check itunes", similarity_score=0.90)
    ]

    decision = default_router.route("unauthorized charge", intent, risk, evidence, evidence_sufficient=True)
    assert decision.decision == "ESCALATE"
    assert "High risk" in decision.reason


def test_router_escalates_on_low_confidence():
    intent = IntentPrediction(intent="BATTERY_POWER", confidence=0.20, reason="Low confidence")
    risk = RiskAssessment(level="LOW", score=0.10, risk_factors=[])
    evidence = [
        EvidenceItem(case_id="c1", customer_message="test", brand_response="restart", similarity_score=0.80)
    ]

    decision = default_router.route("battery issue", intent, risk, evidence, evidence_sufficient=True)
    assert decision.decision == "ESCALATE"
    assert "confidence" in decision.reason.lower()


def test_router_escalates_on_insufficient_evidence():
    intent = IntentPrediction(intent="BATTERY_POWER", confidence=0.90, reason="")
    risk = RiskAssessment(level="LOW", score=0.10, risk_factors=[])

    decision = default_router.route("battery dies", intent, risk, [], evidence_sufficient=False)
    assert decision.decision == "ESCALATE"
    assert "evidence" in decision.reason.lower()


def test_router_auto_handles_safe_inquiry():
    intent = IntentPrediction(intent="SOFTWARE_UPDATE", confidence=0.85, reason="")
    risk = RiskAssessment(level="LOW", score=0.10, risk_factors=[])
    evidence = [
        EvidenceItem(
            case_id="c1",
            customer_message="How to check iOS version?",
            brand_response="Check Settings > General > About.",
            similarity_score=0.85,
            rerank_score=0.88,
        )
    ]

    decision = default_router.route("Where do I check iOS version?", intent, risk, evidence, evidence_sufficient=True)
    assert decision.decision == "AUTO_HANDLE"
    assert "Safe informational inquiry" in decision.reason
