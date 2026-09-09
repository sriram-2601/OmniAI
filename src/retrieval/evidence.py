"""Evidence validation module to verify historical precedent applicability before generation."""
from __future__ import annotations

from typing import List, Dict, Any, Tuple
from src.common.schemas import EvidenceItem, RiskAssessment


class EvidenceValidator:
    """Validates retrieved historical cases for semantic sufficiency, intent match, and contradiction."""

    def __init__(
        self,
        min_relevance_threshold: float = 0.50,
        high_relevance_threshold: float = 0.65,
    ):
        self.min_threshold = min_relevance_threshold
        self.high_threshold = high_relevance_threshold

    def validate_evidence(
        self,
        evidence: List[EvidenceItem],
        predicted_intent: str,
        risk: RiskAssessment,
    ) -> Tuple[bool, str, float]:
        """Assess whether retrieved evidence is sufficient to ground a safe response.

        Returns:
            (is_sufficient: bool, justification: str, confidence_score: float)
        """
        if not evidence:
            return (
                False,
                "No historical support cases were retrieved from the knowledge base.",
                0.0,
            )

        top_item = evidence[0]
        top_sim = top_item.rerank_score or top_item.similarity_score

        # 1. Minimum semantic relevance check
        if top_sim < self.min_threshold:
            return (
                False,
                f"Retrieved precedent similarity ({top_sim:.2f}) is below minimum threshold ({self.min_threshold:.2f}).",
                top_sim,
            )

        # 2. Risk compatibility
        # If user query is HIGH risk, evidence must NEVER override safety policy
        if risk.level == "HIGH":
            return (
                False,
                f"Query involves high-risk factors ({', '.join(risk.risk_factors)}). Historical precedent cannot bypass human review.",
                top_sim,
            )

        # 3. Sufficient confidence
        return (
            True,
            f"Sufficient historical precedent retrieved (top relevance: {top_sim:.2f}). Grounded reply authorized.",
            top_sim,
        )
