"""Failure analysis and error categorization module.

Extracts, categorizes, and analyzes real system failure cases across intent classification,
retrieval relevance, reply quality, and routing safety.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.common.config import RESULTS_DIR


FAILURE_CATEGORIES = {
    "COMPOUND_MULTI_INTENT": {
        "title": "Compound / Multi-Intent Ambiguity",
        "description": "Customer inquiry contains multiple distinct issues (e.g., iOS update failure and battery drain). Single-label classification captures only one aspect or strays.",
        "mitigation": "Migrate to multi-label intent prediction with priority hierarchy (e.g. safety/power issues triage first), or trigger a clarifying question."
    },
    "SLANG_COLLOQUIALISM": {
        "title": "Informal Slang, Sarcasm, and Sarcastic Venting",
        "description": "Customer expresses frustration with Twitter slang, idioms, or sarcasm without naming specific technical symptoms, confusing semantic embeddings.",
        "mitigation": "Augment intent training embeddings with colloquial Twitter support paraphrases and sentiment-aware intent backoff."
    },
    "RARE_HARDWARE_VARIANT": {
        "title": "Rare Hardware Variants & Obsolete Accessories",
        "description": "Customer inquires about vintage devices (e.g. iPod Classic, iPhone 4s) or specific third-party dongles with low representation in historical knowledge base.",
        "mitigation": "Implement device entity extraction; if device is end-of-life or accessory is third-party, escalate immediately with clear vintage device disclosure."
    },
    "OVER_CAUTIOUS_FALSE_ESCALATION": {
        "title": "Over-Cautious False Escalations (Keyword False Positives)",
        "description": "Customer mentions 'account' or 'ID' in an informational/benign context (e.g., 'logged in with Apple ID, how do I change wallpaper?'), falsely tripping credential risk gates.",
        "mitigation": "Contextualize risk detection using dependency parsing or LLM-based risk classifier rather than raw keyword triggers."
    },
    "PRECEDENT_GENERALIZATION": {
        "title": "Precedent Generalization / Canned Deflection",
        "description": "Retriever returns generic troubleshooting steps (e.g., restart device) when the customer has an exact error code or obscure bug needing specific documentation.",
        "mitigation": "Incorporate sparse BM25 / exact token matching for numerical error codes (e.g., 'Error 3194', '0xE80000A') alongside dense semantic search."
    },
}


def analyze_failures(eval_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Inspect evaluation run records and categorize real failures into top 5 failure modes.

    Args:
        eval_records: End-to-end evaluation records for golden set cases.

    Returns:
        Structured failure analysis dictionary with concrete examples and mitigation plans.
    """
    categorized: Dict[str, List[Dict[str, Any]]] = {
        cat: [] for cat in FAILURE_CATEGORIES
    }

    uncategorized = []

    for rec in eval_records:
        msg = rec.get("customer_message", "").lower()
        true_intent = rec.get("expected_intent")
        pred_intent = rec.get("predicted_intent")
        true_action = rec.get("expected_action")
        pred_action = rec.get("actual_decision")
        intent_match = (true_intent == pred_intent)
        action_match = (true_action == pred_action)
        risk_level = rec.get("risk_level", "LOW")

        # Check for failures
        is_failure = not intent_match or not action_match or rec.get("judge_overall", 5.0) < 3.5

        if not is_failure:
            continue

        assigned_cat = None

        # 1. Over-cautious false escalation: Expected AUTO_HANDLE, got ESCALATE, risk triggered by benign mention
        if true_action == "AUTO_HANDLE" and pred_action == "ESCALATE":
            if any(k in msg for k in ["account", "apple id", "icloud", "card", "pay", "charge"]):
                assigned_cat = "OVER_CAUTIOUS_FALSE_ESCALATION"

        # 2. Compound / Multi-Intent
        if not assigned_cat and not intent_match:
            # Check for multiple intent indicators (e.g., battery + update, or screen + sound)
            has_update = any(w in msg for w in ["update", "ios", "11.", "version"])
            has_battery = any(w in msg for w in ["battery", "drain", "charge", "die", "dying"])
            has_screen = any(w in msg for w in ["screen", "display", "freeze", "black"])
            has_sound = any(w in msg for w in ["audio", "sound", "volume", "music", "headphone"])

            count_indicators = sum([has_update, has_battery, has_screen, has_sound])
            if count_indicators >= 2 or " and " in msg:
                assigned_cat = "COMPOUND_MULTI_INTENT"

        # 3. Slang / Colloquialism / Sarcasm
        if not assigned_cat and not intent_match:
            slang_markers = ["wtf", "omg", "wth", "sucks", "trash", "crap", "smh", "tf", "bruh", "ugh", "annoying", "garbage"]
            if any(s in msg for s in slang_markers) or "???" in msg or "!!!" in msg:
                assigned_cat = "SLANG_COLLOQUIALISM"

        # 4. Rare / Obsolete Hardware / Accessories
        if not assigned_cat:
            rare_hardware = ["ipod", "nano", "shuffle", "classic", "dongle", "adapter", "30 pin", "4s", "5c", "beats", "lightning to"]
            if any(rh in msg for rh in rare_hardware):
                assigned_cat = "RARE_HARDWARE_VARIANT"

        # 5. Precedent Generalization (generic draft for specific technical query)
        if not assigned_cat:
            assigned_cat = "PRECEDENT_GENERALIZATION"

        example_entry = {
            "case_id": rec.get("id"),
            "customer_message": rec.get("customer_message"),
            "expected_intent": true_intent,
            "predicted_intent": pred_intent,
            "intent_confidence": rec.get("intent_confidence"),
            "expected_action": true_action,
            "actual_decision": pred_action,
            "escalation_reason": rec.get("escalation_reason"),
            "draft_reply": rec.get("draft_reply"),
            "judge_overall": rec.get("judge_overall"),
            "judge_reason": rec.get("judge_reason"),
        }

        categorized[assigned_cat].append(example_entry)

    # Compile structured summary
    summary_modes = []
    for cat_key, meta in FAILURE_CATEGORIES.items():
        examples = categorized[cat_key]
        summary_modes.append({
            "category_key": cat_key,
            "title": meta["title"],
            "count": len(examples),
            "description": meta["description"],
            "actionable_mitigation": meta["mitigation"],
            "representative_examples": examples[:3],  # Up to 3 concrete real examples
        })

    report = {
        "total_failures_detected": sum(len(exs) for exs in categorized.values()),
        "top_failure_modes": summary_modes,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "failure_examples.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report
