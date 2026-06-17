# Phase 4 — ML Risk Classifier
## spec.md

### Overview
Build, train, evaluate, and serve a financial risk classifier. Given up to 8 financial ratios (all nullable), the model predicts a risk tier (low/medium/high/critical) and returns a 0–100 risk score plus the top 3 SHAP-attributed features explaining the prediction. Inference is cached in Redis. The evaluation script enforces an F1 gate that blocks CI on regression.

### User Stories
- As the system, I call `POST /api/v1/ml/risk-score` with financial ratios and receive a risk tier, score, and 3 SHAP explanations.
- As a developer, calling the same ratios twice returns the second result from Redis instantly.
- As a developer, running `python ml/evaluate.py` exits code 1 if macro F1 < 0.65.
- As an analyst, I see the top 3 features that drove the risk score and which direction they pushed it.

### Requirements
- 8 input features (all `float | None`): `current_ratio`, `debt_to_equity`, `interest_coverage`, `ebitda_margin`, `revenue_growth_yoy`, `cash_burn_rate`, `working_capital_ratio`, `gross_margin`
- scikit-learn Pipeline: `SimpleImputer(strategy="median")` → `StandardScaler()` → `XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42)`
- 4-class output: low (0) / medium (1) / high (2) / critical (3)
- Risk score 0–100: `np.dot(proba, [0, 33, 66, 100])`
- SHAP: `TreeExplainer`, top 3 features by absolute SHAP value for predicted class, with direction and magnitude
- Redis cache key: `ml:risk:{sha256(sorted_json(ratios))}`, TTL `ML_CACHE_TTL` (default 0 = no expiry)
- Evaluation gate: macro F1 >= 0.65 AND no class F1 < 0.50 — else `sys.exit(1)`
- Training data: `ml/data/financial_ratios.csv` — synthetic data acceptable, min 500 rows
- Model artifact: `ml/artifacts/risk_classifier.pkl`
- P95 inference latency < 50ms (synchronous sklearn predict)

### Acceptance Criteria
```bash
python ml/train.py    # artifact created
python ml/evaluate.py  # prints report, exits 0 if gate passes
curl -X POST localhost:8000/api/v1/ml/risk-score \
  -d '{"current_ratio": 0.8, "debt_to_equity": 3.2}' \
  # → {risk_score, risk_tier, contributing_factors: [{feature, value, direction, magnitude}]}
# Call twice with same body → second call returns from Redis (no sklearn call)
# redis-cli keys "ml:risk:*" → shows key
```
