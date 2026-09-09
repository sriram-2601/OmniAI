"""Master Support Agent Pipeline: Integrates Classification, Retrieval, Reranking, Risk, Routing, and Generation."""
from __future__ import annotations

import time
import uuid
from typing import Optional, Dict, Any

from src.common.schemas import (
    AgentOutput,
    IntentPrediction,
    RiskAssessment,
    RoutingDecision,
    EvidenceItem,
)
from src.classifier.classifier import default_classifier, SemanticIntentClassifier
from src.routing.risk import default_risk_classifier, RiskClassifier
from src.retrieval.retrieve import CaseRetriever
from src.retrieval.rerank import CaseReranker
from src.retrieval.evidence import EvidenceValidator
from src.routing.router import default_router, OperationalRouter
from src.generation.generator import default_generator, ReplyGenerator
from src.multilingual.normalizer import MultilingualProcessor
from src.multilingual.multi_brand import BrandRouter


class SupportAgent:
    """Evidence-grounded, risk-aware customer support decision agent for AppleSupport."""

    def __init__(
        self,
        classifier: Optional[SemanticIntentClassifier] = None,
        risk_classifier: Optional[RiskClassifier] = None,
        retriever: Optional[CaseRetriever] = None,
        reranker: Optional[CaseReranker] = None,
        validator: Optional[EvidenceValidator] = None,
        router: Optional[OperationalRouter] = None,
        generator: Optional[ReplyGenerator] = None,
    ):
        self.classifier = classifier or default_classifier
        self.risk_classifier = risk_classifier or default_risk_classifier
        self.retriever = retriever or CaseRetriever()
        self.reranker = reranker or CaseReranker()
        self.validator = validator or EvidenceValidator()
        self.router = router or default_router
        self.generator = generator or default_generator

    def process_message(
        self,
        customer_message: str,
        exclude_case_id: Optional[str] = None,
        top_k_retrieve: int = 15,
        top_k_rerank: int = 3,
    ) -> AgentOutput:
        """Execute end-to-end support pipeline on an incoming customer message."""
        start_time = time.perf_counter()
        req_id = f"req_{uuid.uuid4().hex[:8]}"

        # Step 0: Brand & Multilingual Language Detection
        brand_info = BrandRouter.detect_brand(customer_message)
        normalized_query, lang_label = MultilingualProcessor.normalize_to_semantic_inquiry(customer_message)

        # Step 1: Intent Classification (using normalized semantic query)
        intent = self.classifier.predict_one(normalized_query)

        # Step 2: Risk Assessment
        risk = self.risk_classifier.evaluate_risk(
            normalized_query,
            intent.intent,
            intent.confidence,
        )

        # Step 3: Semantic Retrieval from FAISS Knowledge Base
        raw_evidence = self.retriever.retrieve(
            normalized_query,
            top_k=top_k_retrieve,
            exclude_case_id=exclude_case_id,
        )

        # Step 4: Hybrid Relevance Reranking
        reranked_evidence = self.reranker.rerank(
            customer_message,
            raw_evidence,
            top_k=top_k_rerank,
            predicted_intent=intent.intent,
        )

        # Step 5: Evidence Validation
        evid_ok, evid_reason, evid_score = self.validator.validate_evidence(
            reranked_evidence,
            intent.intent,
            risk,
        )

        # Step 6: Operational Routing Decision (AUTO-HANDLE vs ESCALATE)
        decision = self.router.route(
            customer_message,
            intent,
            risk,
            reranked_evidence,
            evidence_sufficient=evid_ok,
        )

        # Step 7: Evidence-Grounded Reply Generation
        reply, used_ids = self.generator.generate_reply(
            customer_message,
            intent,
            risk,
            decision,
            reranked_evidence,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return AgentOutput(
            request_id=req_id,
            customer_message=customer_message,
            brand=brand_info["name"],
            language=lang_label,
            intent=intent,
            risk=risk,
            evidence=reranked_evidence,
            draft_reply=reply,
            decision=decision,
            latency_ms=round(latency_ms, 2),
            evidence_grounded=evid_ok,
        )


# Global default agent instance
default_agent = SupportAgent()
