"""Reranking module: Hybrid Lexical-Semantic and Resolution Quality Reranker."""
from __future__ import annotations

import re
from typing import List, Optional
from src.common.schemas import EvidenceItem


class CaseReranker:
    """Reranks retrieved historical cases to prioritize substantive, high-relevance resolutions."""

    def __init__(
        self,
        weight_semantic: float = 0.55,
        weight_lexical: float = 0.25,
        weight_substance: float = 0.20,
    ):
        self.w_sem = weight_semantic
        self.w_lex = weight_lexical
        self.w_sub = weight_substance

    def _compute_lexical_overlap(self, query: str, candidate_text: str) -> float:
        """Compute token-level Jaccard overlap between query and historical message."""
        def tokenize(s: str) -> set:
            return set(re.findall(r"\b\w{3,}\b", s.lower()))

        q_tokens = tokenize(query)
        c_tokens = tokenize(candidate_text)
        if not q_tokens or not c_tokens:
            return 0.0

        intersection = len(q_tokens.intersection(c_tokens))
        union = len(q_tokens.union(c_tokens))
        return intersection / union if union > 0 else 0.0

    def _compute_substance_score(self, resolution_text: str) -> float:
        """Score the informational substance of the brand's historical resolution.

        Rewards:
        - Concrete diagnostic steps ('Settings >', 'restart', 'reset', 'update')
        - Official Apple Support links ('support.apple.com')
        - Step-by-step actions

        Penalizes:
        - Pure 'DM us' canned replies with zero troubleshooting content.
        """
        if not resolution_text:
            return 0.0

        score = 0.5  # baseline
        lower_res = resolution_text.lower()

        # Rewards
        if "support.apple.com" in lower_res or "http" in lower_res:
            score += 0.25
        if ">" in resolution_text or "settings" in lower_res:
            score += 0.20
        if any(step in lower_res for step in ["restart", "reset", "backup", "restore", "toggle", "turn off", "sign out"]):
            score += 0.15

        # Penalties for empty deflection
        if re.search(r"send us a direct message|join us in a dm|dm us your", lower_res):
            if len(lower_res.split()) < 15:
                score -= 0.30

        return max(0.0, min(1.0, score))

    def rerank(
        self,
        query: str,
        candidates: List[EvidenceItem],
        top_k: int = 3,
        predicted_intent: Optional[str] = None,
    ) -> List[EvidenceItem]:
        """Rerank candidates using dense similarity, lexical overlap, and resolution substance.

        Args:
            query: Incoming customer message.
            candidates: Top-K items from dense FAISS search.
            top_k: Target number of items to return after reranking.
            predicted_intent: Optional classified intent for consistency checks.

        Returns:
            Pruned and reordered list of EvidenceItems with rerank_score populated.
        """
        if not candidates:
            return []

        scored_candidates = []
        for item in candidates:
            sem_score = item.similarity_score
            lex_score = self._compute_lexical_overlap(query, item.customer_message)
            sub_score = self._compute_substance_score(item.brand_response)

            # Combined score
            final_score = (
                self.w_sem * sem_score
                + self.w_lex * lex_score
                + self.w_sub * sub_score
            )

            # Create updated item with rerank score
            updated_item = EvidenceItem(
                case_id=item.case_id,
                customer_message=item.customer_message,
                brand_response=item.brand_response,
                similarity_score=item.similarity_score,
                rerank_score=round(float(final_score), 4),
                intent_match=item.intent_match,
                resolution_match=sub_score >= 0.4,
            )
            scored_candidates.append(updated_item)

        # Sort descending by rerank score
        scored_candidates.sort(key=lambda x: x.rerank_score or 0.0, reverse=True)
        return scored_candidates[:top_k]
