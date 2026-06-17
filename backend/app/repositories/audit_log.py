from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    """INSERT-only repository for the audit trail."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        tenant_id: UUID,
        actor_id: UUID,
        actor_email: str,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: UUID | None = None,
        resource_name: str | None = None,
        deal_room_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        entry = AuditLog(
            tenant_id=tenant_id,
            deal_room_id=deal_room_id,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            metadata_=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(entry)
