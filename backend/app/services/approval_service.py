"""Approval service: role checks, disputed annotation guard, approval transaction."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report
from app.models.report_approval import ReportApproval
from app.repositories.annotation import AnnotationRepository
from app.repositories.deal_room import DealRoomRepository


async def assert_can_approve(
    deal_room_id: uuid.UUID,
    report_id: uuid.UUID,
    current_user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> int:
    """Raise 403 if user lacks role; raise 409 if disputed annotations remain.

    Returns the count of unresolved disputes resolved prior to approval (always 0
    when it succeeds — callers use the return only to populate disputed_resolved_count).
    """
    dr_repo = DealRoomRepository(session, tenant_id, current_user_id)
    role = await dr_repo.get_user_role(deal_room_id, current_user_id)
    if role not in ("owner", "senior_analyst"):
        raise HTTPException(403, "Only senior analysts and owners can approve")

    ann_repo = AnnotationRepository(session, tenant_id)
    disputed = await ann_repo.get_unresolved_disputed_count(report_id)
    if disputed > 0:
        raise HTTPException(
            409, f"{disputed} disputed annotation(s) must be resolved first"
        )
    return 0


async def approve_report(
    report: Report,
    approved_by: uuid.UUID,
    tenant_id: uuid.UUID,
    session: AsyncSession,
    sign_off_notes: str | None = None,
) -> ReportApproval:
    """Transition report status to approved and create a ReportApproval record."""
    report.status = "approved"
    approval = ReportApproval(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        report_id=report.id,
        approved_by=approved_by,
        approved_at=datetime.now(timezone.utc),
        sign_off_notes=sign_off_notes,
        disputed_resolved_count=0,
    )
    session.add(approval)
    await session.flush()
    await session.refresh(approval)
    return approval
