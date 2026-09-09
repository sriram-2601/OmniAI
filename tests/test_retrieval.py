"""Unit tests for FAISS vector retrieval, leakage exclusion, reranking, and evidence validation."""
from __future__ import annotations

import pytest
from src.retrieval.index import SupportCaseIndex, INDEX_FILE_PATH, METADATA_FILE_PATH
from src.retrieval.retrieve import CaseRetriever
from src.retrieval.rerank import CaseReranker
from src.retrieval.evidence import EvidenceValidator
from src.common.schemas import RiskAssessment


def test_index_and_metadata_exist():
    assert INDEX_FILE_PATH.exists(), "Missing faiss_index.bin"
    assert METADATA_FILE_PATH.exists(), "Missing faiss_metadata.json"
    assert INDEX_FILE_PATH.stat().st_size > 1000000


def test_retriever_query():
    retriever = CaseRetriever()
    query = "My iPhone battery dies within 30 minutes after iOS 11 update."
    results = retriever.retrieve(query, top_k=5)

    assert len(results) == 5
    for item in results:
        assert item.case_id
        assert item.customer_message
        assert item.brand_response
        assert 0.0 <= item.similarity_score <= 1.0

    # Ensure results are sorted descending
    for i in range(len(results) - 1):
        assert results[i].similarity_score >= results[i + 1].similarity_score


def test_retrieval_leakage_exclusion():
    retriever = CaseRetriever()
    query = "Bluetooth audio keeps disconnecting in my car"
    first_results = retriever.retrieve(query, top_k=5)
    target_id = first_results[0].case_id

    # Exclude the top result
    filtered_results = retriever.retrieve(query, top_k=5, exclude_case_id=target_id)
    retrieved_ids = [r.case_id for r in filtered_results]

    assert target_id not in retrieved_ids, f"Leakage detected! Excluded case {target_id} was returned."


def test_reranker():
    retriever = CaseRetriever()
    reranker = CaseReranker()
    query = "Where can I check my current iOS version on iPhone?"

    raw_results = retriever.retrieve(query, top_k=10)
    assert len(raw_results) == 10

    reranked = reranker.rerank(query, raw_results, top_k=3)
    assert len(reranked) == 3

    for item in reranked:
        assert item.rerank_score is not None
        assert 0.0 <= item.rerank_score <= 1.0

    # Ensure reranked is sorted descending by rerank_score
    for i in range(len(reranked) - 1):
        assert (reranked[i].rerank_score or 0.0) >= (reranked[i + 1].rerank_score or 0.0)


def test_evidence_validator():
    validator = EvidenceValidator(min_relevance_threshold=0.45)
    retriever = CaseRetriever()

    results = retriever.retrieve("My iPhone battery is draining", top_k=3)

    # Valid low risk
    low_risk = RiskAssessment(level="LOW", score=0.1, risk_factors=[])
    is_ok, reason, score = validator.validate_evidence(results, "BATTERY_POWER", low_risk)
    assert is_ok is True
    assert score > 0.40

    # High risk should reject automation even if evidence is found
    high_risk = RiskAssessment(level="HIGH", score=0.9, risk_factors=["fraud", "dispute"])
    is_ok_hr, reason_hr, _ = validator.validate_evidence(results, "APP_STORE_BILLING", high_risk)
    assert is_ok_hr is False
    assert "high-risk" in reason_hr.lower()
