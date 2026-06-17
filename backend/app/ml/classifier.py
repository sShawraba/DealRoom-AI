import asyncio
import json
import pickle
from hashlib import sha256

import numpy as np
import shap
import structlog
from fastapi import HTTPException

from app.core.config import settings
from app.core.redis import get_redis
from app.schemas.ml import FinancialRatios, RiskScoreResponse, SHAPFactor

log = structlog.get_logger(__name__)

FEATURES = [
    "current_ratio",
    "debt_to_equity",
    "interest_coverage",
    "ebitda_margin",
    "revenue_growth_yoy",
    "cash_burn_rate",
    "working_capital_ratio",
    "gross_margin",
]

RISK_TIERS = ["low", "medium", "high", "critical"]


class RiskClassifier:
    def __init__(self):
        with open(settings.ML_MODEL_PATH, "rb") as f:
            self.pipeline = pickle.load(f)
        clf = self.pipeline.named_steps["clf"]
        self.explainer = shap.TreeExplainer(clf)
        self._preproc = self.pipeline[:-1]

    def predict(self, ratios: FinancialRatios) -> RiskScoreResponse:
        X = np.array([[getattr(ratios, f) for f in FEATURES]], dtype=float)
        missing = [FEATURES[i] for i, v in enumerate(X[0]) if np.isnan(v)]

        proba = self.pipeline.predict_proba(X)[0]
        risk_score = float(np.dot(proba, [0, 33, 66, 100]))
        predicted_class = int(np.argmax(proba))
        tier = RISK_TIERS[predicted_class]

        X_pre = self._preproc.transform(X)
        shap_values = self.explainer.shap_values(X_pre)

        # Handle both old SHAP (list per class) and new SHAP (3-D array).
        # Old: list of n_classes arrays each (n_samples, n_features) → stack → (n_classes, n_samples, n_features)
        # New: (n_samples, n_features, n_classes)
        sv = np.array(shap_values) if isinstance(shap_values, list) else shap_values
        if sv.ndim == 3:
            if sv.shape[0] == 1:
                # New SHAP: (n_samples=1, n_features, n_classes)
                class_shap = sv[0, :, predicted_class]
            else:
                # Old SHAP stacked: (n_classes, n_samples=1, n_features)
                class_shap = sv[predicted_class, 0, :]
        else:
            class_shap = sv[0]

        top3_idx = np.argsort(np.abs(class_shap))[::-1][:3]
        factors = [
            SHAPFactor(
                feature=FEATURES[i],
                value=float(X[0][i]) if not np.isnan(X[0][i]) else None,
                direction="increases_risk" if class_shap[i] > 0 else "decreases_risk",
                magnitude=float(abs(class_shap[i])),
            )
            for i in top3_idx
        ]

        return RiskScoreResponse(
            risk_score=round(risk_score, 1),
            risk_tier=tier,
            contributing_factors=factors,
            missing_features=missing,
        )

    async def predict_cached(self, ratios: FinancialRatios) -> RiskScoreResponse:
        redis = await get_redis()
        cache_input = json.dumps(ratios.model_dump(), sort_keys=True)
        key = f"ml:risk:{sha256(cache_input.encode()).hexdigest()}"

        cached = await redis.get(key)
        if cached:
            return RiskScoreResponse.model_validate_json(cached)

        result = await asyncio.to_thread(self.predict, ratios)
        payload = result.model_dump_json()

        if settings.ML_CACHE_TTL > 0:
            await redis.setex(key, settings.ML_CACHE_TTL, payload)
        else:
            await redis.set(key, payload)

        return result


risk_classifier: RiskClassifier | None = None


async def get_risk_classifier() -> RiskClassifier:
    if risk_classifier is None:
        raise HTTPException(status_code=503, detail="ML model not loaded")
    return risk_classifier
