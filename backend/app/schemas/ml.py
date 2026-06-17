from typing import Optional

from pydantic import BaseModel


class FinancialRatios(BaseModel):
    current_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    interest_coverage: Optional[float] = None
    ebitda_margin: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    cash_burn_rate: Optional[float] = None
    working_capital_ratio: Optional[float] = None
    gross_margin: Optional[float] = None


class SHAPFactor(BaseModel):
    feature: str
    value: Optional[float]
    direction: str
    magnitude: float


class RiskScoreResponse(BaseModel):
    risk_score: float
    risk_tier: str
    contributing_factors: list[SHAPFactor]
    missing_features: list[str]
