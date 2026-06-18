"""Pydantic schemas for ManagementQuestion Q&A."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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


class QASendEmailRequest(BaseModel):
    recipient_email: str


class QAGenerateResponse(BaseModel):
    generated: int
    questions: list[ManagementQuestionResponse]
