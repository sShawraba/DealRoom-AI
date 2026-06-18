"""Pydantic schemas for document permission management."""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel


class PermissionGrant(BaseModel):
    user_id: Optional[uuid.UUID] = None
    role: Optional[str] = None
    can_view: bool = True
    can_download: bool = False


class PermissionUpdateRequest(BaseModel):
    mode: str = "restricted"
    grants: list[PermissionGrant] = []


class PermissionGrantResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    user_id: uuid.UUID | None
    role: str | None
    can_view: bool
    can_download: bool
    granted_by: uuid.UUID | None

    model_config = {"from_attributes": True}
