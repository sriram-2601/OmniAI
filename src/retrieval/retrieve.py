"""Semantic vector retrieval from FAISS historical case index."""
from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.retrieval.index import SupportCaseIndex, INDEX_FILE_PATH, METADATA_FILE_PATH
from src.common.schemas import EvidenceItem


class CaseRetriever:
    """Retrieves top-k historically similar support cases using dense FAISS vector search."""

    def __init__(self, case_index: Optional[SupportCaseIndex] = None):
        if case_index is not None:
            self.case_index = case_index
        else:
            self.case_index = SupportCaseIndex()
            if INDEX_FILE_PATH.exists() and METADATA_FILE_PATH.exists():
                self.case_index.load(INDEX_FILE_PATH, METADATA_FILE_PATH)
            else:
                print("[Retriever] Index not found on disk. Building from knowledge_base_sample.jsonl...")
                self.case_index.build_from_jsonl()

    def retrieve(
        self,
        query: str,
        top_k: int = 15,
        exclude_case_id: Optional[str] = None,
    ) -> List[EvidenceItem]:
        """Retrieve top-k nearest historical support cases.

        Args:
            query: Incoming customer problem text.
            top_k: Number of historical cases to retrieve.
            exclude_case_id: Optional ID to exclude (prevents evaluation leakage).

        Returns:
            List of EvidenceItem objects sorted by similarity.
        """
        if not query or not query.strip() or self.case_index.index is None:
            return []

        # Encode query to unit vector
        query_emb = self.case_index.encoder.encode([query], convert_to_numpy=True, normalize_embeddings=True)

        # Search extra candidates if excluding a case
        fetch_k = top_k + 2 if exclude_case_id else top_k
        fetch_k = min(fetch_k, self.case_index.index.ntotal)

        distances, indices = self.case_index.index.search(query_emb, fetch_k)

        raw_dists = distances[0]
        raw_indices = indices[0]

        evidence_items: List[EvidenceItem] = []
        for sim, idx in zip(raw_dists, raw_indices):
            if idx < 0 or idx >= len(self.case_index.cases_metadata):
                continue

            case_meta = self.case_index.cases_metadata[idx]
            case_id = str(case_meta.get("conversation_id", f"case_{idx}"))

            # Leakage prevention: Never return the query's own conversation
            if exclude_case_id and case_id == str(exclude_case_id):
                continue

            cust_msg = case_meta.get("initial_customer_problem", "")
            resolution = case_meta.get("resolution", "")

            item = EvidenceItem(
                case_id=case_id,
                customer_message=cust_msg,
                brand_response=resolution,
                similarity_score=round(float(sim), 4),
                intent_match=True,
                resolution_match=True,
            )
            evidence_items.append(item)

            if len(evidence_items) >= top_k:
                break

        return evidence_items
