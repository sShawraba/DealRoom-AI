# Phase 4 Ml Classifier
## tasks.md

- [ ] **Task 01** — Write `ml/data/generate_data.py`: generates 600-row CSV with 8 feature columns (realistic ranges with NaN for ~15% of values) + `label` column using thresholds from plan.md. Run it: `python ml/data/generate_data.py`
- [ ] **Task 02 [needs 01]** — Write `ml/train.py`: load CSV, build Pipeline (SimpleImputer→StandardScaler→XGBClassifier params from spec), 5-fold stratified CV, print CV F1/ROC-AUC, fit on full data, `joblib.dump` to `ml/artifacts/risk_classifier.pkl`
- [ ] **Task 03 [needs 02]** — Write `ml/evaluate.py`: load model + test split, print `classification_report`, check macro F1>=0.65 AND min class F1>=0.50, exit 1 if gate fails, save SHAP summary plot to `ml/artifacts/shap_summary.png`
- [ ] **Task 04 [needs 02]** — Run `python ml/train.py` → verify artifact created. Run `python ml/evaluate.py` → verify gate passes (exits 0)
- [ ] **Task 05** — Write `app/schemas/ml.py`: `FinancialRatios` (8 Optional[float] fields), `SHAPFactor` (feature, value, direction, magnitude), `RiskScoreResponse` (risk_score, risk_tier, contributing_factors, missing_features)
- [ ] **Task 06 [needs 05]** — Write `app/ml/classifier.py`: `RiskClassifier` class with `predict()` and `predict_cached()` from plan.md. Global `risk_classifier: RiskClassifier | None = None` singleton. `get_risk_classifier()` dependency that raises 503 if not loaded.
- [ ] **Task 07 [needs 06]** — Update `app/main.py` lifespan: load `RiskClassifier()` into `ml_module.risk_classifier` when `ML_MODEL_PATH` exists
- [ ] **Task 08** — Write `app/ml/features.py`: `extract_ratios_from_chunks(chunks: list[str], session) -> FinancialRatios` — single gpt-4o-mini call with extraction prompt, parse JSON response, return FinancialRatios (nulls where not found)
- [ ] **Task 09 [needs 05,06]** — Write `app/routers/ml.py`: `POST /api/v1/ml/risk-score`, accepts `FinancialRatios`, calls `classifier.predict_cached()`, returns `RiskScoreResponse`. Register in `main.py`.
- [ ] **Task 10 [needs 04,09]** — Write `tests/test_ml.py`: POST with known ratios → verify response shape, risk_score 0-100, contributing_factors has 3 items with direction field. POST same ratios twice → verify second returns from Redis. POST with all nulls → verify missing_features populated, still returns valid response.
- [ ] **Task 11 [needs 10]** — Run `pytest tests/test_ml.py -v` — all pass

- [ ] **Task 12 (asyncio.to_thread)** — sklearn's `predict()` and `predict_proba()` are CPU-bound. Wrap them in `predict_cached()`:
    ```python
    result = await asyncio.to_thread(self.predict, ratios)
    ```
    The synchronous `predict()` method stays synchronous. Only the public `predict_cached()` is async.
- [ ] **Task 13 (cache admin endpoint)** — Add `DELETE /api/v1/admin/cache/ml` to `app/routers/admin.py` that calls `invalidate_ml_cache()`. Owner role required. Log `cache.ml_invalidated` to audit trail.
- [ ] **Task 14 (lru_cache check)** — Confirm `get_settings()` in `app/core/config.py` has `@lru_cache(maxsize=1)`. If not, add it. Also add `@lru_cache` to any other pure helper functions in `app/ml/features.py` that compute static mappings (e.g. feature name lists, threshold dicts).