"""Operational Router: Safe escalation policy and confidence-gated decision engine."""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.common.config import CONFIGS_DIR
from src.common.schemas import IntentPrediction, RiskAssessment, RoutingDecision, EvidenceItem


class OperationalRouter:
    """Decides whether to AUTO-HANDLE a message or ESCALATE to a human agent."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = Path(config_path) if config_path else (CONFIGS_DIR / "thresholds.yaml")
        self.thresholds = self._load_thresholds()

    def _load_thresholds(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("thresholds", {})
        return {
            "min_intent_confidence": 0.40,
            "min_evidence_similarity": 0.45,
            "auto_handle_rules": {
                "max_permitted_risk_level": "LOW",
                "min_intent_confidence": 0.40,
                "min_evidence_relevance": 0.45,
            },
        }

    def route(
        self,
        customer_message: str,
        intent: IntentPrediction,
        risk: RiskAssessment,
        evidence: List[EvidenceItem],
        evidence_sufficient: bool,
    ) -> RoutingDecision:
        """Evaluate escalation policy and return an audit-traceable routing decision."""
        safety_flags: List[str] = []
        rules = self.thresholds.get("auto_handle_rules", {})
        min_intent_conf = rules.get("min_intent_confidence", 0.40)
        min_evid_sim = rules.get("min_evidence_relevance", 0.45)

        # Gate 1: High Risk is ALWAYS escalated (Zero tolerance policy)
        if risk.level == "HIGH":
            safety_flags.extend(risk.risk_factors)
            return RoutingDecision(
                decision="ESCALATE",
                reason=f"High risk policy override: {risk.risk_factors[0]}",
                confidence=risk.score,
                safety_flags=safety_flags,
            )

        # Gate 2: Medium Risk is escalated for customer retention / safety
        if risk.level == "MEDIUM":
            safety_flags.extend(risk.risk_factors)
            return RoutingDecision(
                decision="ESCALATE",
                reason=f"Medium risk flag: {risk.risk_factors[0]}",
                confidence=risk.score,
                safety_flags=safety_flags,
            )

        # Gate 3: Low Intent Confidence Escalator
        if intent.confidence < min_intent_conf:
            flag = f"Low intent confidence ({intent.confidence:.2f} < {min_intent_conf:.2f})"
            safety_flags.append(flag)
            return RoutingDecision(
                decision="ESCALATE",
                reason=f"Ambiguous query intent; confidence ({intent.confidence:.2f}) insufficient for auto-reply.",
                confidence=round(1.0 - intent.confidence, 2),
                safety_flags=safety_flags,
            )

        # Gate 4: Insufficient Evidence or Out-of-Distribution Precedent
        if not evidence or not evidence_sufficient:
            flag = "Insufficient historical evidence"
            safety_flags.append(flag)
            return RoutingDecision(
                decision="ESCALATE",
                reason="Insufficient historical evidence / precedent to ground a safe answer.",
                confidence=0.75,
                safety_flags=safety_flags,
            )

        top_evidence_score = evidence[0].rerank_score or evidence[0].similarity_score
        if top_evidence_score < min_evid_sim:
            flag = f"Low evidence relevance ({top_evidence_score:.2f} < {min_evid_sim:.2f})"
            safety_flags.append(flag)
            return RoutingDecision(
                decision="ESCALATE",
                reason=f"Top historical precedent relevance ({top_evidence_score:.2f}) is below safe threshold ({min_evid_sim:.2f}).",
                confidence=0.70,
                safety_flags=safety_flags,
            )

        # Gate 5: Safe Auto-Handle Authorized
        return RoutingDecision(
            decision="AUTO_HANDLE",
            reason=(
                f"Safe informational inquiry (Risk: LOW). "
                f"Confident intent match ({intent.intent}, {intent.confidence:.2f}) "
                f"with verified historical precedent (Relevance: {top_evidence_score:.2f})."
            ),
            confidence=round((intent.confidence + top_evidence_score) / 2.0, 2),
            safety_flags=[],
        )


# Global instance
default_router = OperationalRouter()
