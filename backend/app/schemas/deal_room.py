from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DealRoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_company: str = Field(min_length=1, max_length=255)
    description: str | None = None


class DealRoomUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    target_company: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: str | None = None


class DealRoomResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    target_company: str
    description: str | None
    status: str
    risk_tier: str | None
    risk_score: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DealRoomMemberResponse(BaseModel):
    id: uuid.UUID
    deal_room_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    invited_by: uuid.UUID | None
    invited_at: datetime
    full_name: str | None = None
    email: str | None = None

    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "analyst"


class UpdateMemberRoleRequest(BaseModel):
    role: str
