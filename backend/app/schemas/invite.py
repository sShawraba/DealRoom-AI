from __future__ import annotations

from pydantic import BaseModel, Field


class InviteInfoResponse(BaseModel):
    email: str
    invited_by_name: str
    deal_room_name: str | None
    deal_room_role: str | None


class InviteAcceptRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)
