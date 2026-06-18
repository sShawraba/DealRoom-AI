"""Pydantic schemas for ManagementQuestion Q&A."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from bleach import clean
from pydantic import BaseModel, field_validator


class ManagementQuestionResponse(BaseModel):
    id: uuid.UUID
    deal_room_id: uuid.UUID
    report_id: uuid.UUID
    source_item_id: uuid.UUID | None
    category: str
    question: str
    priority: str
    answered: bool
    answer_notes: str | None
    answered_by: uuid.UUID | None
    answered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class QAGroupedResponse(BaseModel):
    """Questions grouped by category."""
    categories: dict[str, list[ManagementQuestionResponse]]


class QAAnswerPatch(BaseModel):
    answer_notes: str

    @field_validator("answer_notes")
    @classmethod
    def sanitise_answer_notes(cls, v: str) -> str:
        return clean(v, tags=[], strip=True) if v else v


class QASendEmailRequest(BaseModel):
    recipient_email: str


class QAGenerateResponse(BaseModel):
    generated: int
    questions: list[ManagementQuestionResponse]
