from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from fastapi import Request
    from app.models.audit_log import AuditLog


class AuditAction:
    USER_LOGIN = "user.login"
    USER_LOGIN_FAILED = "user.login_failed"
    USER_REGISTERED = "user.registered"
    DEAL_ROOM_CREATED = "deal_room.created"
    DEAL_ROOM_UPDATED = "deal_room.updated"
    DEAL_ROOM_DELETED = "deal_room.deleted"
    DEAL_ROOM_ACCESSED = "deal_room.accessed"
    MEMBER_INVITED = "permission.member_invited"
    MEMBER_REMOVED = "permission.member_removed"
    ROLE_CHANGED = "permission.role_changed"
    # Phase 2+
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_DOWNLOADED = "document.downloaded"
    DOCUMENT_DELETED = "document.deleted"
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    REPORT_SUBMITTED = "report.submitted_for_review"
    REPORT_APPROVED = "report.approved"
    ANNOTATION_CREATED = "annotation.created"
    ANNOTATION_DISPUTED = "annotation.disputed"
    ANNOTATION_RESOLVED = "annotation.resolved"
    REPORT_ITEM_EDITED = "report.item_edited"
    REPORT_EXPORTED = "report.exported"
    QA_GENERATED = "qa.generated"
    QA_EMAIL_SENT = "qa.email_sent"
    GUARDRAIL_CONTENT_FLAGGED = "guardrail.content_flagged"
    PERMISSION_DOCUMENT_RESTRICTED = "permission.document_restricted"


async def log_event(
    session: AsyncSession,
    actor_id: UUID,
    actor_email: str,
    actor_role: str,
    tenant_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    resource_name: str | None = None,
    deal_room_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
    request: "Request | None" = None,
) -> None:
    """
    Insert an audit log row in the current session/transaction.

    Does NOT commit — caller controls the transaction boundary.
    """
    from app.models.audit_log import AuditLog

    ip: str | None = None
    ua: str | None = None
    if request is not None:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

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
        ip_address=ip,
        user_agent=ua,
    )
    session.add(entry)
