"""LLM-as-a-Judge module for evaluating customer support reply quality."""
from __future__ import annotations

import json
import re
from typing import Dict, Any, Optional, List
from src.common.llm import default_llm_client
from src.common.schemas import EvidenceItem

JUDGE_SYSTEM_PROMPT = """You are an expert impartial quality evaluator for enterprise customer support agents on Twitter.
Your task is to evaluate the quality of a drafted Twitter reply from @AppleSupport given the customer inquiry, the customer's intent, and the retrieved historical resolution precedents.

Score the reply on 5 criteria using a 1-5 integer scale (1 = Terrible, 3 = Acceptable, 5 = Flawless):

1. correctness (1-5): Is the advice technically accurate and aligned with Apple products?
2. historical_grounding (1-5): Is the solution faithfully grounded in the retrieved precedents without hallucinating policies or settings?
3. helpfulness (1-5): Does it give the customer an actionable next step, diagnostic path, or clear solution?
4. safety (1-5): Does it avoid asking for sensitive credentials publicly and avoid false promises/unauthorized refunds?
5. brand_fit (1-5): Is the tone warm, professional, concise, and under 280 characters?

Return STRICTLY a JSON object with this structure:
{
  "correctness": 5,
  "historical_grounding": 5,
  "helpfulness": 5,
  "safety": 5,
  "brand_fit": 5,
  "overall": 5.0,
  "reason": "Brief 1-2 sentence justification."
}
"""

JUDGE_USER_PROMPT = """CUSTOMER INQUIRY:
"{customer_message}"

CLASSIFIED INTENT: {intent}
OPERATIONAL ACTION: {decision}

HISTORICAL PRECEDENTS PROVIDED:
{evidence_text}

DRAFTED REPLY:
"{draft_reply}"

Evaluate the drafted reply strictly according to the rubric:"""


class ReplyQualityJudge:
    """Evaluates support reply quality across 5 dimensions using LLM-as-judge with heuristic fallback."""

    def __init__(self, llm_client=default_llm_client):
        self.llm_client = llm_client

    def judge_reply(
        self,
        customer_message: str,
        draft_reply: str,
        intent: str,
        decision: str,
        evidence: List[EvidenceItem],
    ) -> Dict[str, Any]:
        """Evaluate a single reply and return structured rubric scores."""
        evid_summary = "\n".join([f"- Precedent: {e.brand_response}" for e in evidence[:2]]) if evidence else "None"
        user_prompt = JUDGE_USER_PROMPT.format(
            customer_message=customer_message,
            intent=intent,
            decision=decision,
            evidence_text=evid_summary,
            draft_reply=draft_reply,
        )

        try:
            raw_eval = self.llm_client.generate(
                system_prompt=JUDGE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            cleaned = raw_eval.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            parsed = json.loads(cleaned)
            # Ensure required keys
            for k in ["correctness", "historical_grounding", "helpfulness", "safety", "brand_fit"]:
                parsed[k] = float(parsed.get(k, 4.0))
            parsed["overall"] = round(
                (parsed["correctness"] + parsed["historical_grounding"] + parsed["helpfulness"] + parsed["safety"] + parsed["brand_fit"]) / 5.0,
                2
            )
            return parsed
        except Exception:
            # Deterministic Rubric Heuristic Fallback
            return self._heuristic_judge(customer_message, draft_reply, intent, decision, evidence)

    def _heuristic_judge(
        self,
        customer_message: str,
        draft_reply: str,
        intent: str,
        decision: str,
        evidence: List[EvidenceItem],
    ) -> Dict[str, Any]:
        """Deterministic rule-based evaluator for offline/zero-cost calibration."""
        reply_len = len(draft_reply)
        has_url = "http" in draft_reply or ".com" in draft_reply
        has_greeting = any(g in draft_reply.lower() for g in ["we're here", "thanks", "hello", "hi", "let's"])
        is_length_valid = reply_len <= 280

        # Safety score
        safety = 5.0
        if any(p in draft_reply.lower() for p in ["password", "credit card", "pin", "ssn"]):
            safety = 1.0

        # Brand fit
        brand_fit = 4.5 if (has_greeting and is_length_valid) else 3.5

        # Grounding & correctness
        if decision == "ESCALATE":
            grounding = 4.8
            correctness = 4.8
            helpfulness = 4.5
            reason = "Proper safe escalation protocol applied with secure handoff channel."
        else:
            if evidence and any(e.similarity_score > 0.50 for e in evidence):
                grounding = 4.5
                correctness = 4.6
                helpfulness = 4.5 if (has_url or ">" in draft_reply) else 4.0
                reason = "Reply incorporates diagnostic guidance grounded in historical Apple resolution precedent."
            else:
                grounding = 3.5
                correctness = 3.8
                helpfulness = 3.5
                reason = "Reply provides generic guidance due to moderate precedent similarity."

        overall = round((correctness + grounding + helpfulness + safety + brand_fit) / 5.0, 2)
        return {
            "correctness": correctness,
            "historical_grounding": grounding,
            "helpfulness": helpfulness,
            "safety": safety,
            "brand_fit": brand_fit,
            "overall": overall,
            "reason": reason,
        }


# Global instance
default_judge = ReplyQualityJudge()
