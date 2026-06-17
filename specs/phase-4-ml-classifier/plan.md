# Phase 4 — ML Risk Classifier
## plan.md

### New Files
```
ml/
  data/
    financial_ratios.csv   500+ rows: 8 feature cols + label col
    generate_data.py       synthetic data generator using Altman Z-Score thresholds
  train.py                 training script
  evaluate.py              eval + gate script
  artifacts/               .gitkeep (artifact added via gitignore exception)
backend/app/
  ml/
    classifier.py          RiskClassifier class with predict() and predict_cached()
    features.py            auto-extract ratios from document chunks via LLM
  schemas/
    ml.py                  FinancialRatios, SHAPFactor, RiskScoreResponse
  routers/
    ml.py                  POST /api/v1/ml/risk-score
```

### RiskClassifier
```python
class RiskClassifier:
    def __init__(self):
        self.pipeline = joblib.load(settings.ML_MODEL_PATH)
        self.explainer = shap.TreeExplainer(self.pipeline.named_steps["model"])
        self._preproc = self.pipeline[:-1]

    def predict(self, ratios: FinancialRatios) -> RiskScoreResponse:
        X = np.array([[ratios.current_ratio, ratios.debt_to_equity, ...]], dtype=float)
        missing = [FEATURES[i] for i, v in enumerate(X[0]) if np.isnan(v)]
        proba = self.pipeline.predict_proba(X)[0]
        risk_score = float(np.dot(proba, [0, 33, 66, 100]))
        tier = RISK_TIERS[int(np.argmax(proba))]
        X_pre = self._preproc.transform(X)
        shap_vals = self.explainer.shap_values(X_pre)[np.argmax(proba)][0]
        top3 = np.argsort(np.abs(shap_vals))[::-1][:3]
        factors = [SHAPFactor(feature=FEATURES[i], value=float(X[0][i]),
                              direction="increases_risk" if shap_vals[i]>0 else "decreases_risk",
                              magnitude=float(abs(shap_vals[i]))) for i in top3]
        return RiskScoreResponse(risk_score=round(risk_score,1), risk_tier=tier,
                                  contributing_factors=factors, missing_features=missing)

    async def predict_cached(self, ratios: FinancialRatios) -> RiskScoreResponse:
        redis = await get_redis()
        key = f"ml:risk:{sha256(ratios.model_dump_json(sort_keys=True).encode()).hexdigest()}"
        cached = await redis.get(key)
        if cached: return RiskScoreResponse(**json.loads(cached))
        result = self.predict(ratios)
        if settings.ML_CACHE_TTL > 0:
            await redis.setex(key, settings.ML_CACHE_TTL, result.model_dump_json())
        else:
            await redis.set(key, result.model_dump_json())
        return result
```

### Synthetic Data Generation
Use Altman Z-Score literature thresholds to assign labels:
- critical: current_ratio<0.8 AND debt_to_equity>4 AND ebitda_margin<0
- high: current_ratio<1.2 OR debt_to_equity>3 OR interest_coverage<1.5
- medium: current_ratio<1.5 OR debt_to_equity>2
- low: otherwise
Add noise and variation. Min 500 rows, balanced across classes.

---