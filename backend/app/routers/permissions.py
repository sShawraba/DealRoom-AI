"""Document permission management endpoints for Phase 7."""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import delete, select

from app.core.audit import AuditAction, log_event
from app.core.deps import CurrentUser, CurrentUserDep, SessionDep
from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.repositories.deal_room import DealRoomRepository
from app.services.document_service import grant_default_permissions

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["permissions"])

SENIOR_ROLES = {"owner", "senior_analyst"}


# ── Schemas ───────────────────────────────────────────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dr_repo(session, current_user: CurrentUser) -> DealRoomRepository:
    return DealRoomRepository(session, current_user.tenant_id, current_user.id)


async def _get_document_and_check_role(
    doc_id: uuid.UUID,
    session,
    current_user: CurrentUser,
) -> Document:
    """Return the document or raise 404; also assert the caller has a senior role."""
    result = await session.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    repo = _dr_repo(session, current_user)
    user_role = await repo.get_user_role(doc.deal_room_id, current_user.id)
    if user_role not in SENIOR_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Requires owner or senior_analyst role in the deal room",
        )
    return doc


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.patch("/{doc_id}/permissions", response_model=list[PermissionGrantResponse])
async def update_permissions(
    doc_id: uuid.UUID,
    body: PermissionUpdateRequest,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    """Replace all permission grants for a document. Owner/senior_analyst only."""
    doc = await _get_document_and_check_role(doc_id, session, current_user)

    await session.execute(
        delete(DocumentPermission).where(DocumentPermission.document_id == doc_id)
    )
    await session.flush()

    if body.mode == "default":
        await grant_default_permissions(
            document_id=doc_id,
            deal_room_id=doc.deal_room_id,
            tenant_id=current_user.tenant_id,
            session=session,
        )
    else:
        for grant in body.grants:
            if grant.user_id is None and grant.role is None:
                continue
            perm = DocumentPermission(
                tenant_id=current_user.tenant_id,
                document_id=doc_id,
                user_id=grant.user_id,
                role=grant.role,
                can_view=grant.can_view,
                can_download=grant.can_download,
                granted_by=current_user.id,
            )
            session.add(perm)
        await session.flush()

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.PERMISSION_DOCUMENT_RESTRICTED,
        resource_type="document",
        resource_id=doc_id,
        deal_room_id=doc.deal_room_id,
        metadata={"mode": body.mode, "grant_count": len(body.grants)},
        request=request,
    )

    result = await session.execute(
        select(DocumentPermission).where(DocumentPermission.document_id == doc_id)
    )
    perms = list(result.scalars().all())
    await session.commit()

    log.info("permissions.updated", doc_id=str(doc_id), mode=body.mode)
    return perms


@router.get("/{doc_id}/permissions", response_model=list[PermissionGrantResponse])
async def get_permissions(
    doc_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    """List all permission grants for a document. Owner/senior_analyst only."""
    await _get_document_and_check_role(doc_id, session, current_user)

    result = await session.execute(
        select(DocumentPermission).where(
            DocumentPermission.document_id == doc_id,
            DocumentPermission.tenant_id == current_user.tenant_id,
        )
    )
    return list(result.scalars().all())
