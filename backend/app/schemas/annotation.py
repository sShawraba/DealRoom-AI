"""Pydantic schemas for Annotation and AnnotationReply."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class AnnotationCreate(BaseModel):
    report_item_id: uuid.UUID
    content: str
    type: Literal["comment", "verified", "disputed"] = "comment"


class AnnotationPatch(BaseModel):
    resolved: bool | None = None
    type: Literal["comment", "verified", "disputed"] | None = None


class AnnotationReplyCreate(BaseModel):
    content: str


class AnnotationReplyResponse(BaseModel):
    id: uuid.UUID
    annotation_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnotationResponse(BaseModel):
    id: uuid.UUID
    deal_room_id: uuid.UUID
    report_item_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    type: str
    resolved: bool
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnnotationsByItemResponse(BaseModel):
    """Keyed by report_item_id (str UUID) → list of annotations."""
    annotations: dict[str, list[AnnotationResponse]]
    total: int
    page: int
    page_size: int
