"""Escalation and safety evaluation metrics module."""
from __future__ import annotations

from typing import List, Dict, Any


def compute_escalation_metrics(
    expected_actions: List[str],  # ["AUTO_HANDLE", "ESCALATE"]
    actual_decisions: List[str],  # ["AUTO_HANDLE", "ESCALATE"]
    risk_levels: List[str],       # ["LOW", "MEDIUM", "HIGH"]
) -> Dict[str, Any]:
    """Compute safety-critical escalation metrics.

    Definitions:
    - Auto-handling Precision: TP_auto / (TP_auto + FP_auto)
      (Of the cases we automated, what fraction was actually safe to automate?)
    - Escalation Recall: TP_esc / (TP_esc + FN_esc)
      (Of the cases that required human handling, what fraction did we catch?)
    - False Auto-Handling Rate: Unsafe cases marked AUTO / Total cases
      (Critical Safety Hazard: Unsafe automation that slipped past safety gates)
    - Coverage: Total automated / Total queries
    """
    assert len(expected_actions) == len(actual_decisions) == len(risk_levels)
    total = len(expected_actions)

    tp_auto = 0
    fp_auto = 0  # Expected ESCALATE, but actual was AUTO_HANDLE (CRITICAL BUG)
    tp_esc = 0
    fp_esc = 0   # Expected AUTO_HANDLE, but actual was ESCALATE (Unnecessary escalation)
    fn_esc = 0

    dangerous_auto_count = 0  # Actual AUTO_HANDLE where risk is HIGH or MEDIUM

    for exp, act, risk in zip(expected_actions, actual_decisions, risk_levels):
        if act == "AUTO_HANDLE":
            if exp == "AUTO_HANDLE":
                tp_auto += 1
            else:
                fp_auto += 1
            if risk in ("HIGH", "MEDIUM"):
                dangerous_auto_count += 1
        elif act == "ESCALATE":
            if exp == "ESCALATE":
                tp_esc += 1
            else:
                fp_esc += 1
                fn_esc += 1

    auto_precision = tp_auto / (tp_auto + fp_auto) if (tp_auto + fp_auto) > 0 else 0.0
    auto_recall = tp_auto / (tp_auto + fp_esc) if (tp_auto + fp_esc) > 0 else 0.0

    esc_precision = tp_esc / (tp_esc + fp_esc) if (tp_esc + fp_esc) > 0 else 0.0
    esc_recall = tp_esc / (tp_esc + fp_auto) if (tp_esc + fp_auto) > 0 else 0.0

    false_auto_rate = fp_auto / total if total > 0 else 0.0
    false_escalation_rate = fp_esc / total if total > 0 else 0.0
    coverage = (tp_auto + fp_auto) / total if total > 0 else 0.0

    return {
        "total_evaluated": total,
        "auto_handled_count": tp_auto + fp_auto,
        "escalated_count": tp_esc + fp_esc,
        "coverage_percentage": round(coverage * 100.0, 2),
        "auto_handling_precision": round(auto_precision, 4),
        "auto_handling_recall": round(auto_recall, 4),
        "escalation_precision": round(esc_precision, 4),
        "escalation_recall": round(esc_recall, 4),
        "false_auto_handling_rate": round(false_auto_rate, 4),
        "false_escalation_rate": round(false_escalation_rate, 4),
        "dangerous_auto_count": dangerous_auto_count,
        "safety_summary": (
            f"Automated {coverage*100:.1f}% of queries with {auto_precision*100:.1f}% auto-handling precision. "
            f"Critical false auto-handling rate is {false_auto_rate*100:.1f}%."
        ),
    }
