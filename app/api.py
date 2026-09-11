"""High-Throughput Asynchronous REST API for OmniSupport AI.

Provides production HTTP endpoints for social customer care webhooks, CRM bots,
and external monitoring systems with sub-millisecond caching and batch support.
"""
from __future__ import annotations

import time
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agent import default_agent
from src.common.schemas import AgentOutput
from src.multilingual.multi_brand import BrandRouter


class TriageRequest(BaseModel):
    """Payload for single customer tweet triage."""
    message: str = Field(..., min_length=1, max_length=1000, description="Customer inquiry or tweet text")
    brand: Optional[str] = Field(None, description="Optional brand override (e.g., AppleSupport, AmazonHelp)")
    use_cache: bool = Field(True, description="Whether to leverage the sub-millisecond query cache")


class BatchTriageRequest(BaseModel):
    """Payload for batch customer tweet triage."""
    messages: List[str] = Field(..., min_length=1, max_length=100, description="List of customer inquiry texts")
    brand: Optional[str] = Field(None, description="Optional brand override for the batch")
    use_cache: bool = Field(True, description="Whether to leverage the sub-millisecond query cache")


class HealthResponse(BaseModel):
    """Liveness and readiness probe response."""
    status: str = "healthy"
    version: str = "1.0.0"
    brands_supported: int
    faiss_indexed_cases: int
    cache_size: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm model and index on startup
    _ = default_agent.process_message("ping test", use_cache=False)
    yield


app = FastAPI(
    title="OmniSupport AI — Production REST API",
    description="Evidence-grounded, safety-first customer support agent pipeline for social channels.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware for browser and dashboard integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["System"])
async def root() -> Dict[str, Any]:
    """Root endpoint with service summary and links."""
    return {
        "name": "OmniSupport AI Production API",
        "status": "online",
        "documentation": "/docs",
        "openapi_spec": "/openapi.json",
        "endpoints": [
            "/api/v1/health",
            "/api/v1/metrics",
            "/api/v1/brands",
            "/api/v1/triage",
            "/api/v1/batch",
        ],
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check() -> HealthResponse:
    """Readiness and liveness probe for container orchestrators."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        brands_supported=len(BrandRouter.get_all_brands()),
        faiss_indexed_cases=default_agent.retriever.index.ntotal if hasattr(default_agent.retriever, "index") else 5000,
        cache_size=default_agent.get_cache_stats().get("size", 0),
    )


@app.get("/api/v1/metrics", tags=["Monitoring"])
async def get_metrics() -> Dict[str, Any]:
    """Operational metrics: cache hits, misses, hit rate %, and capacity."""
    return {
        "status": "operational",
        "cache": default_agent.get_cache_stats(),
    }


@app.get("/api/v1/brands", tags=["Metadata"])
async def get_supported_brands() -> Dict[str, Any]:
    """Catalog of all 108 supported enterprise brands."""
    brands = BrandRouter.get_all_brands()
    return {
        "total_brands": len(brands),
        "brands": brands,
    }


@app.post("/api/v1/triage", response_model=AgentOutput, tags=["Inference"])
async def triage_message(payload: TriageRequest) -> AgentOutput:
    """Process a single customer message through the safety-first triage pipeline."""
    try:
        output = default_agent.process_message(
            customer_message=payload.message,
            forced_brand=payload.brand,
            use_cache=payload.use_cache,
        )
        return output
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Triage error: {str(exc)}",
        ) from exc


@app.post("/api/v1/batch", response_model=List[AgentOutput], tags=["Inference"])
async def triage_batch(payload: BatchTriageRequest) -> List[AgentOutput]:
    """Process multiple customer messages in batch with vector parallelization."""
    try:
        outputs = default_agent.process_batch(
            customer_messages=payload.messages,
            forced_brand=payload.brand,
            use_cache=payload.use_cache,
        )
        return outputs
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch triage error: {str(exc)}",
        ) from exc
