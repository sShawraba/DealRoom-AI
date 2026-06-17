# Phase 4 — ML Risk Classifier: Implementation Summary

## Files Created
| File | Purpose |
|------|---------|
| `backend/app/schemas/ml.py` | `FinancialRatios`, `SHAPFactor`, `RiskScoreResponse` Pydantic models |
| `backend/app/ml/__init__.py` | Package init |
| `backend/app/ml/classifier.py` | `RiskClassifier` with `predict()` + `asyncio.to_thread` `predict_cached()`, Redis cache, `get_risk_classifier()` 503 dependency |
| `backend/app/ml/features.py` | `extract_ratios_from_chunks()` — single gpt-4o-mini call; `@lru_cache` on static helpers |
| `backend/app/routers/ml.py` | `POST /api/v1/ml/risk-score` |
| `backend/tests/test_ml.py` | 3 pytest tests |

## Files Modified
| File | Change |
|------|--------|
| `backend/app/main.py` | Register `ml_router` in `create_app()` |
| `backend/app/routers/admin.py` | Add `DELETE /api/v1/admin/cache/ml` (owner role, logs `cache.ml_invalidated`) |

## Pre-existing (no changes needed)
- `ml/train.py`, `ml/evaluate.py`, `ml/data/generate_data.py` — already written
- `ml/artifacts/risk_classifier.pkl` — already trained
- `backend/app/main.py` lifespan ML block — already present
- `backend/app/core/config.py` `@lru_cache`, `ML_MODEL_PATH`, `ML_CACHE_TTL` — already present

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `POST /api/v1/ml/risk-score` → risk_score, risk_tier, contributing_factors | ✅ |
| Same ratios twice → second from Redis (key verified) | ✅ |
| All-null ratios → missing_features=8, valid response | ✅ |
| `pytest tests/test_ml.py -v` → 3 passed | ✅ |
| `DELETE /api/v1/admin/cache/ml` (owner only) | ✅ |
| `asyncio.to_thread` wrapping CPU-bound predict | ✅ |
| `@lru_cache` on `get_settings()` and static helpers | ✅ |

## Notes
- sklearn version mismatch warning (1.9 pkl → 1.5 in Docker): functionally compatible; retrain in-container to eliminate.
- Cache key: `ml:risk:{sha256(json.dumps(ratios.model_dump(), sort_keys=True))}`, TTL governed by `ML_CACHE_TTL` (0 = indefinite).
- SHAP handles both old-list and new-3D-array format from SHAP 0.45.
