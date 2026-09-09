"""Pydantic data models and schemas used throughout the support agent pipeline."""
from __future__ import annotations

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class TweetRecord(BaseModel):
    """Raw tweet record matching Kaggle dataset schema."""
    tweet_id: str
    author_id: str
    inbound: bool
    created_at: str
    text: str
    response_tweet_id: Optional[str] = None
    in_reply_to_tweet_id: Optional[str] = None


class MessageTurn(BaseModel):
    """Single turn within a conversation."""
    tweet_id: str
    author_id: str
    role: Literal["customer", "brand"]
    text: str
    timestamp: str


class Conversation(BaseModel):
    """Reconstructed multi-turn conversation thread."""
    conversation_id: str
    brand: str
    customer_author_id: str
    initial_customer_problem: str
    customer_messages: List[str] = Field(default_factory=list)
    brand_messages: List[str] = Field(default_factory=list)
    full_thread: List[MessageTurn] = Field(default_factory=list)
    start_time: str
    end_time: str
    turn_count: int
    resolution: Optional[str] = None


class SupportCase(BaseModel):
    """Historical support case stored in vector database."""
    case_id: str
    brand: str
    customer_message: str
    brand_response: str
    intent: Optional[str] = None
    resolution_summary: Optional[str] = None
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentPrediction(BaseModel):
    """Structured intent classification output."""
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    probabilities: Optional[Dict[str, float]] = None


class RiskAssessment(BaseModel):
    """Risk layer classification output."""
    level: Literal["LOW", "MEDIUM", "HIGH"]
    score: float = Field(ge=0.0, le=1.0)
    risk_factors: List[str] = Field(default_factory=list)
    requires_human_verification: bool = False


class EvidenceItem(BaseModel):
    """Retrieved historical precedent item."""
    case_id: str
    customer_message: str
    brand_response: str
    similarity_score: float
    rerank_score: Optional[float] = None
    intent_match: bool = True
    resolution_match: bool = True


class RoutingDecision(BaseModel):
    """Final operational decision: AUTO-HANDLE vs ESCALATE."""
    decision: Literal["AUTO_HANDLE", "ESCALATE"]
    reason: str
    confidence: float
    safety_flags: List[str] = Field(default_factory=list)


class AgentOutput(BaseModel):
    """Complete trace of the agent's decision and generation."""
    request_id: str
    customer_message: str
    brand: str = "AppleSupport"
    language: str = "English"
    intent: IntentPrediction
    risk: RiskAssessment
    evidence: List[EvidenceItem] = Field(default_factory=list)
    draft_reply: str
    decision: RoutingDecision
    latency_ms: float = 0.0
    evidence_grounded: bool = True


class GoldenExample(BaseModel):
    """Hand-labelled evaluation benchmark case."""
    id: str
    customer_message: str
    conversation_context: Optional[str] = ""
    intent: str
    expected_action: Literal["AUTO_HANDLE", "ESCALATE"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    escalation_reason: str
    notes: Optional[str] = ""
    retrieval_ground_truth_ids: Optional[List[str]] = Field(default_factory=list)
