"""Pydantic schemas for deal-room comparison and precedent search."""
from __future__ import annotations

import uuid

from pydantic import BaseModel


class DealRoomComparisonItem(BaseModel):
    id: uuid.UUID
    name: str
    target_company: str
    risk_score: float | None
    risk_tier: str | None
    red_flag_count: int
    financial_snapshot: list[str]
    top_findings: list[str]


class CompareResponse(BaseModel):
    deal_rooms: list[DealRoomComparisonItem]


class DealRoomSearchResult(BaseModel):
    id: uuid.UUID
    name: str
    target_company: str
    risk_tier: str | None
    match_score: float
