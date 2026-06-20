"""Audit log endpoints — list and CSV export. Owner/manager only."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.deps import CurrentUserDep, SessionDep
from app.repositories.audit_log import AuditLogRepository
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse

router = APIRouter(prefix="/api/v1/audit-log", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_log(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    actor_email: str | None = Query(None),
    actions: str | None = Query(None, description="Comma-separated action names"),
    date_from: str | None = Query(None, description="ISO date e.g. 2024-01-01"),
    date_to: str | None = Query(None, description="ISO date e.g. 2024-12-31"),
) -> AuditLogListResponse:
    repo = AuditLogRepository(session)

    parsed_from: datetime | None = None
    parsed_to: datetime | None = None
    if date_from:
        try:
            parsed_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    if date_to:
        try:
            parsed_to = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            pass

    action_list = [a.strip() for a in actions.split(",") if a.strip()] if actions else None

    rows, total = await repo.list(
        tenant_id=current_user.tenant_id,
        page=page,
        page_size=page_size,
        actor_email=actor_email or None,
        actions=action_list,
        date_from=parsed_from,
        date_to=parsed_to,
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.from_orm(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/export")
async def export_audit_log_csv(
    session: SessionDep,
    current_user: CurrentUserDep,
    actor_email: str | None = Query(None),
    actions: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> StreamingResponse:
    repo = AuditLogRepository(session)

    parsed_from: datetime | None = None
    parsed_to: datetime | None = None
    if date_from:
        try:
            parsed_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    if date_to:
        try:
            parsed_to = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            pass

    action_list = [a.strip() for a in actions.split(",") if a.strip()] if actions else None

    # Fetch up to 10 000 rows for export
    rows, _ = await repo.list(
        tenant_id=current_user.tenant_id,
        page=1,
        page_size=10_000,
        actor_email=actor_email or None,
        actions=action_list,
        date_from=parsed_from,
        date_to=parsed_to,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "occurred_at", "actor_email", "actor_role",
        "action", "resource_type", "resource_name",
        "deal_room_id", "ip_address",
    ])
    for r in rows:
        writer.writerow([
            r.id,
            r.occurred_at.isoformat() if r.occurred_at else "",
            r.actor_email,
            r.actor_role,
            r.action,
            r.resource_type,
            r.resource_name or "",
            str(r.deal_room_id) if r.deal_room_id else "",
            str(r.ip_address) if r.ip_address else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit-log.csv"},
    )
