from typing import Annotated

import structlog
from fastapi import APIRouter, Depends

from app.ml.classifier import RiskClassifier, get_risk_classifier
from app.schemas.ml import FinancialRatios, RiskScoreResponse

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/ml", tags=["ml"])


@router.post("/risk-score", response_model=RiskScoreResponse)
async def risk_score(
    ratios: FinancialRatios,
    classifier: Annotated[RiskClassifier, Depends(get_risk_classifier)],
) -> RiskScoreResponse:
    return await classifier.predict_cached(ratios)
