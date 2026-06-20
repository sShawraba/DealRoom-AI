from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    """INSERT-only repository for the audit trail."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        actor_email: str,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        resource_name: str | None = None,
        deal_room_id: uuid.UUID | None = None,
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

    async def list(
        self,
        tenant_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        actor_email: str | None = None,
        actions: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        base_q = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if actor_email:
            base_q = base_q.where(AuditLog.actor_email.ilike(f"%{actor_email}%"))
        if actions:
            base_q = base_q.where(AuditLog.action.in_(actions))
        if date_from:
            base_q = base_q.where(AuditLog.occurred_at >= date_from)
        if date_to:
            base_q = base_q.where(AuditLog.occurred_at <= date_to)

        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await self.session.execute(count_q)).scalar_one()

        rows = (
            await self.session.execute(
                base_q
                .order_by(AuditLog.occurred_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()

        return list(rows), total
