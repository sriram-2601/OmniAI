"""Test Suite for Scalability Layer: In-Memory Query Cache, Batch Triage, and REST API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.common.cache import QueryCache
from src.agent import default_agent
from app.api import app


def test_query_cache_put_and_get():
    """Verify basic put, get, and hit/miss accounting in QueryCache."""
    cache = QueryCache(max_size=5)
    key1 = cache.compute_key("My iPhone screen is cracked")
    assert cache.get(key1) is None
    assert cache.misses == 1
    assert cache.hits == 0

    # Obtain a real agent output to store
    output = default_agent.process_message("My iPhone screen is cracked", use_cache=False)
    cache.put(key1, output)

    cached = cache.get(key1)
    assert cached is not None
    assert cached.intent.intent == output.intent.intent
    assert cached.decision.decision == output.decision.decision
    assert cache.hits == 1
    assert cached.latency_ms <= 1.0


def test_query_cache_lru_eviction():
    """Verify that QueryCache strictly enforces max_size via LRU eviction."""
    cache = QueryCache(max_size=3)
    dummy_out = default_agent.process_message("Battery dying fast", use_cache=False)

    keys = [f"key_{i}" for i in range(5)]
    for k in keys:
        cache.put(k, dummy_out)

    stats = cache.stats()
    assert stats["size"] == 3
    assert stats["evictions"] == 2
    # Oldest keys (key_0, key_1) must have been evicted
    assert cache.get("key_0") is None
    assert cache.get("key_1") is None
    # Latest keys (key_2, key_3, key_4) must be present
    assert cache.get("key_4") is not None


def test_agent_caching_speedup():
    """Verify that consecutive identical inquiries achieve sub-millisecond latency."""
    default_agent.clear_cache()
    query = "How do I update to iOS 11 on my iPad?"

    # First call: Cold inference
    out1 = default_agent.process_message(query, use_cache=True)
    stats1 = default_agent.get_cache_stats()
    assert stats1["misses"] >= 1

    # Second call: Cache hit
    out2 = default_agent.process_message(query, use_cache=True)
    stats2 = default_agent.get_cache_stats()
    assert stats2["hits"] >= 1
    assert out2.latency_ms < 5.0  # Sub-millisecond cached lookup
    assert out2.intent.intent == out1.intent.intent
    assert out2.decision.decision == out1.decision.decision


def test_agent_batch_processing():
    """Verify high-throughput batch triage processing."""
    queries = [
        "My battery is draining within 2 hours",
        "Forgot my Apple ID password please help",
        "Wi-Fi keeps dropping on MacBook",
    ]
    batch_results = default_agent.process_batch(queries, use_cache=True)
    assert len(batch_results) == 3
    assert batch_results[0].intent.intent == "BATTERY_POWER"
    assert batch_results[1].decision.decision == "ESCALATE"
    assert batch_results[2].intent.intent == "CONNECTIVITY_NETWORK"


def test_fastapi_endpoints():
    """Verify FastAPI endpoints: /health, /metrics, /brands, /triage, /batch."""
    client = TestClient(app)

    # 1. Root & Health
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json()["status"] == "online"

    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"
    assert res_health.json()["brands_supported"] >= 7

    # 2. Metrics & Brands
    res_metrics = client.get("/api/v1/metrics")
    assert res_metrics.status_code == 200
    assert "cache" in res_metrics.json()

    res_brands = client.get("/api/v1/brands")
    assert res_brands.status_code == 200
    assert "AppleSupport" in res_brands.json()["brands"]

    # 3. Single Triage Endpoint
    res_triage = client.post(
        "/api/v1/triage",
        json={"message": "Can I replace my iPhone battery at the Apple Store?", "use_cache": True},
    )
    assert res_triage.status_code == 200
    data = res_triage.json()
    assert "intent" in data
    assert "decision" in data
    assert "draft_reply" in data

    # 4. Batch Triage Endpoint
    res_batch = client.post(
        "/api/v1/batch",
        json={
            "messages": [
                "Screen is not responding to touch",
                "Unauthorized charge on my account",
            ],
            "use_cache": True,
        },
    )
    assert res_batch.status_code == 200
    batch_data = res_batch.json()
    assert len(batch_data) == 2
    assert batch_data[1]["decision"]["decision"] == "ESCALATE"
