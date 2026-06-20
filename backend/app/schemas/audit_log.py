"""Pydantic schemas for AuditLog."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    tenant_id: uuid.UUID
    deal_room_id: uuid.UUID | None
    actor_id: uuid.UUID
    actor_email: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: uuid.UUID | None
    resource_name: str | None
    metadata: dict[str, Any]
    ip_address: str | None
    user_agent: str | None
    occurred_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj) -> "AuditLogResponse":
        return cls(
            id=obj.id,
            tenant_id=obj.tenant_id,
            deal_room_id=obj.deal_room_id,
            actor_id=obj.actor_id,
            actor_email=obj.actor_email,
            actor_role=obj.actor_role,
            action=obj.action,
            resource_type=obj.resource_type,
            resource_id=obj.resource_id,
            resource_name=obj.resource_name,
            metadata=obj.metadata_,
            ip_address=str(obj.ip_address) if obj.ip_address else None,
            user_agent=obj.user_agent,
            occurred_at=obj.occurred_at,
        )


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
