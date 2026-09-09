"""End-to-end tests for the complete SupportAgent decision and generation pipeline."""
from __future__ import annotations

import pytest
from src.agent import default_agent
from src.common.schemas import AgentOutput


def test_agent_end_to_end_battery_query():
    query = "My iPhone 7 battery is draining from 100% to 10% in just two hours after the latest update."
    output: AgentOutput = default_agent.process_message(query)

    assert isinstance(output, AgentOutput)
    assert output.request_id.startswith("req_")
    assert output.intent.intent == "BATTERY_POWER"
    assert output.intent.confidence > 0.30
    assert len(output.evidence) > 0
    assert len(output.draft_reply) > 0
    assert len(output.draft_reply) <= 280
    assert output.latency_ms > 0


def test_agent_end_to_end_high_risk_escalation():
    query = "Someone hacked my Apple ID and made an unauthorized charge of $150 on my credit card!"
    output: AgentOutput = default_agent.process_message(query)

    assert output.risk.level == "HIGH"
    assert output.decision.decision == "ESCALATE"
    assert "DM" in output.draft_reply or "https://" in output.draft_reply
    assert len(output.draft_reply) <= 280
