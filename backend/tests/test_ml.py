"""
Tests for Phase 4 — ML Risk Classifier endpoint.

Requires the real Docker stack (Redis) and the trained artifact at ml/artifacts/risk_classifier.pkl.
The fixture loads the classifier directly so tests pass regardless of lifespan ML_MODEL_PATH.
"""
import json
import os

import pytest
import pytest_asyncio

from app.core.config import settings

# Use settings path (works in Docker: /app/ml/artifacts/risk_classifier.pkl)
LOCAL_PKL = settings.ML_MODEL_PATH

KNOWN_RATIOS = {
    "current_ratio": 0.8,
    "debt_to_equity": 3.2,
    "interest_coverage": None,
    "ebitda_margin": None,
    "revenue_growth_yoy": None,
    "cash_burn_rate": None,
    "working_capital_ratio": None,
    "gross_margin": None,
}

ALL_NULL_RATIOS = {
    "current_ratio": None,
    "debt_to_equity": None,
    "interest_coverage": None,
    "ebitda_margin": None,
    "revenue_growth_yoy": None,
    "cash_burn_rate": None,
    "working_capital_ratio": None,
    "gross_margin": None,
}


@pytest_asyncio.fixture(scope="session", autouse=True)
async def load_ml_model():
    """Load the real model artifact and inject it into the module singleton."""
    import app.ml.classifier as ml_module
    from app.core.config import settings

    original_path = settings.ML_MODEL_PATH
    settings.ML_MODEL_PATH = LOCAL_PKL

    if os.path.exists(LOCAL_PKL):
        ml_module.risk_classifier = ml_module.RiskClassifier()
    else:
        pytest.skip(f"ML artifact not found at {LOCAL_PKL}")

    yield

    settings.ML_MODEL_PATH = original_path
    ml_module.risk_classifier = None


@pytest.mark.asyncio
async def test_risk_score_response_shape(app_client):
    """POST with known ratios → valid response shape and risk_score in [0, 100]."""
    resp = await app_client.post("/api/v1/ml/risk-score", json=KNOWN_RATIOS)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert "risk_score" in body
    assert "risk_tier" in body
    assert "contributing_factors" in body
    assert "missing_features" in body

    assert 0.0 <= body["risk_score"] <= 100.0
    assert body["risk_tier"] in ("low", "medium", "high", "critical")

    factors = body["contributing_factors"]
    assert len(factors) == 3
    for f in factors:
        assert "feature" in f
        assert "direction" in f
        assert "magnitude" in f
        assert f["direction"] in ("increases_risk", "decreases_risk")


@pytest.mark.asyncio
async def test_risk_score_redis_cache(app_client):
    """POST same ratios twice → second call returns from Redis (key exists)."""
    from app.core.redis import get_redis
    import hashlib

    cache_input = json.dumps(KNOWN_RATIOS, sort_keys=True)
    expected_key = f"ml:risk:{hashlib.sha256(cache_input.encode()).hexdigest()}"

    redis = await get_redis()
    await redis.delete(expected_key)

    resp1 = await app_client.post("/api/v1/ml/risk-score", json=KNOWN_RATIOS)
    assert resp1.status_code == 200

    cached = await redis.get(expected_key)
    assert cached is not None, "Cache key should exist after first call"

    resp2 = await app_client.post("/api/v1/ml/risk-score", json=KNOWN_RATIOS)
    assert resp2.status_code == 200
    assert resp1.json()["risk_score"] == resp2.json()["risk_score"]
    assert resp1.json()["risk_tier"] == resp2.json()["risk_tier"]


@pytest.mark.asyncio
async def test_risk_score_all_nulls(app_client):
    """POST with all null ratios → missing_features populated, still valid response."""
    resp = await app_client.post("/api/v1/ml/risk-score", json=ALL_NULL_RATIOS)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert len(body["missing_features"]) == 8
    assert 0.0 <= body["risk_score"] <= 100.0
    assert len(body["contributing_factors"]) == 3
