"""Pydantic schemas for Report and ReportItem."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from bleach import clean
from pydantic import BaseModel, field_validator


class ReportItemResponse(BaseModel):
    id: uuid.UUID
    section_type: str
    content: str
    citation: dict[str, Any] | None
    is_verified: bool
    item_index: int
    edited_content: str | None = None
    edited_by: uuid.UUID | None = None
    edited_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportSummary(BaseModel):
    id: uuid.UUID
    deal_room_id: uuid.UUID
    status: str
    risk_score: float | None
    risk_tier: str | None
    citation_coverage: float | None
    has_unverified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: uuid.UUID
    deal_room_id: uuid.UUID
    created_by: uuid.UUID
    status: str
    risk_score: float | None
    risk_tier: str | None
    risk_shap_factors: list[dict] | None
    citation_coverage: float | None
    has_unverified: bool
    missing_context: dict | None
    error_message: str | None
    items: list[ReportItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SectionOutput(BaseModel):
    """Schema for LLM-generated section items."""

    class Item(BaseModel):
        content: str
        citation: dict[str, Any] | None = None
        is_verified: bool = True

    items: list[Item]


class ReportCreate(BaseModel):
    pass


class ReportItemEditBody(BaseModel):
    edited_content: str


class ReportStatusBody(BaseModel):
    action: str  # "submit_for_review" | "approve"
    sign_off_notes: str | None = None

    @field_validator("sign_off_notes")
    @classmethod
    def sanitise_sign_off_notes(cls, v: str | None) -> str | None:
        return clean(v, tags=[], strip=True) if v else v
