import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.core.audit import AuditAction, log_event
from app.core.config import settings
from app.core.deps import CurrentUser, CurrentUserDep, SessionDep
from app.models.invite_token import InviteToken
from app.models.user import User
from app.repositories.deal_room import DealRoomRepository
from app.services.document_service import grant_permissions_for_new_member
from app.services.email_service import send_invite_email
from app.schemas.deal_room import (
    DealRoomCreate,
    DealRoomMemberResponse,
    DealRoomResponse,
    DealRoomUpdate,
    InviteMemberRequest,
    UpdateMemberRoleRequest,
)
from app.schemas.pagination import PaginatedResponse

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/deal-rooms", tags=["deal-rooms"])

OWNER_ROLES = {"owner"}
SENIOR_ROLES = {"owner", "senior_analyst"}


def _repo(session, current_user: CurrentUser) -> DealRoomRepository:
    return DealRoomRepository(session, current_user.tenant_id, current_user.id)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[DealRoomResponse])
async def list_deal_rooms(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    from app.models.annotation import Annotation
    from app.models.document import Document

    repo = _repo(session, current_user)
    items, total = await repo.list_all(page=page, page_size=page_size)

    room_ids = [r.id for r in items]
    doc_counts: dict = {}
    annotation_counts: dict = {}
    if room_ids:
        doc_rows = (await session.execute(
            select(Document.deal_room_id, func.count(Document.id).label("cnt"))
            .where(
                Document.deal_room_id.in_(room_ids),
                Document.tenant_id == current_user.tenant_id,
            )
            .group_by(Document.deal_room_id)
        )).all()
        doc_counts = {r.deal_room_id: r.cnt for r in doc_rows}

        ann_rows = (await session.execute(
            select(Annotation.deal_room_id, func.count(Annotation.id).label("cnt"))
            .where(
                Annotation.deal_room_id.in_(room_ids),
                Annotation.tenant_id == current_user.tenant_id,
                Annotation.type == "disputed",
                Annotation.resolved == False,  # noqa: E712
            )
            .group_by(Annotation.deal_room_id)
        )).all()
        annotation_counts = {r.deal_room_id: r.cnt for r in ann_rows}

    enriched = [
        DealRoomResponse(
            id=r.id,
            tenant_id=r.tenant_id,
            created_by=r.created_by,
            name=r.name,
            target_company=r.target_company,
            description=r.description,
            status=r.status,
            risk_tier=r.risk_tier,
            risk_score=r.risk_score,
            document_count=doc_counts.get(r.id, 0),
            unresolved_annotations=annotation_counts.get(r.id, 0),
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in items
    ]
    return PaginatedResponse(items=enriched, total=total, page=page, page_size=page_size)


@router.post("", response_model=DealRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_deal_room(
    body: DealRoomCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create deal rooms")
    repo = _repo(session, current_user)
    room = await repo.create(
        created_by=current_user.id,
        name=body.name,
        target_company=body.target_company,
        description=body.description,
    )
    await repo.add_member(
        deal_room_id=room.id,
        user_id=current_user.id,
        role="owner",
        invited_by=None,
    )
    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.DEAL_ROOM_CREATED,
        resource_type="deal_room",
        resource_id=room.id,
        resource_name=room.name,
        request=request,
    )
    await session.commit()
    log.info("deal_room.created", id=str(room.id), name=room.name)
    return room


@router.get("/{room_id}", response_model=DealRoomResponse)
async def get_deal_room(
    room_id: UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    repo = _repo(session, current_user)
    room = await repo.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Deal room not found")

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.DEAL_ROOM_ACCESSED,
        resource_type="deal_room",
        resource_id=room.id,
        resource_name=room.name,
        deal_room_id=room.id,
        request=request,
    )
    await session.commit()
    return room


@router.patch("/{room_id}", response_model=DealRoomResponse)
async def update_deal_room(
    room_id: UUID,
    body: DealRoomUpdate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    repo = _repo(session, current_user)
    room = await repo.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Deal room not found")

    user_role = await repo.get_user_role(room_id, current_user.id)
    if user_role not in SENIOR_ROLES:
        raise HTTPException(status_code=403, detail="Requires owner or senior_analyst role")

    updates = body.model_dump(exclude_none=True)
    room = await repo.update(room_id, **updates)
    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.DEAL_ROOM_UPDATED,
        resource_type="deal_room",
        resource_id=room_id,
        deal_room_id=room_id,
        request=request,
    )
    await session.commit()
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal_room(
    room_id: UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    repo = _repo(session, current_user)
    room = await repo.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Deal room not found")

    user_role = await repo.get_user_role(room_id, current_user.id)
    if user_role not in OWNER_ROLES:
        raise HTTPException(status_code=403, detail="Requires owner role")

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.DEAL_ROOM_DELETED,
        resource_type="deal_room",
        resource_id=room_id,
        resource_name=room.name,
        deal_room_id=room_id,
        request=request,
    )
    await repo.delete(room_id)
    await session.commit()


# ── Member management ─────────────────────────────────────────────────────────

@router.get("/{room_id}/members", response_model=PaginatedResponse[DealRoomMemberResponse])
async def list_members(
    room_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List all members of a deal room (paginated)."""
    repo = _repo(session, current_user)
    room = await repo.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Deal room not found")
    all_members = await repo.list_members(room_id)

    user_ids = [m.user_id for m in all_members]
    users_by_id = {}
    if user_ids:
        rows = (await session.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        users_by_id = {u.id: u for u in rows}

    def _enrich(m):
        u = users_by_id.get(m.user_id)
        return DealRoomMemberResponse(
            id=m.id,
            deal_room_id=m.deal_room_id,
            user_id=m.user_id,
            role=m.role,
            invited_by=m.invited_by,
            invited_at=m.invited_at,
            full_name=u.full_name if u else None,
            email=u.email if u else None,
        )

    start = (page - 1) * page_size
    page_items = [_enrich(m) for m in all_members[start: start + page_size]]
    return PaginatedResponse(
        items=page_items,
        total=len(all_members),
        page=page,
        page_size=page_size,
    )


@router.post("/{room_id}/members", status_code=201)
async def invite_member(
    room_id: UUID,
    body: InviteMemberRequest,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    repo = _repo(session, current_user)
    room = await repo.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Deal room not found")

    user_role = await repo.get_user_role(room_id, current_user.id)
    if user_role not in OWNER_ROLES:
        raise HTTPException(status_code=403, detail="Requires owner role")

    invitee = (
        await session.execute(
            select(User).where(
                User.email == body.email,
                User.tenant_id == current_user.tenant_id,
            )
        )
    ).scalar_one_or_none()

    if invitee is None:
        # User doesn't have an account yet — send an email invite
        token_str = secrets.token_urlsafe(32)
        invite = InviteToken(
            tenant_id=current_user.tenant_id,
            invited_by_id=current_user.id,
            email=body.email,
            token=token_str,
            deal_room_id=room_id,
            deal_room_role=body.role,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(invite)
        await log_event(
            session=session,
            actor_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            tenant_id=current_user.tenant_id,
            action=AuditAction.USER_INVITED,
            resource_type="invite_token",
            resource_name=body.email,
            deal_room_id=room_id,
            metadata={"invited_role": body.role, "email": body.email},
            request=request,
        )
        await session.commit()

        accept_url = f"{settings.APP_URL}/accept-invite?token={token_str}"
        try:
            await send_invite_email(
                to=body.email,
                invited_by_name=current_user.full_name,
                deal_room_name=room.name,
                accept_url=accept_url,
            )
        except Exception:
            log.warning("invite.email_failed", email=body.email)

        return JSONResponse(
            status_code=202,
            content={"status": "invited", "email": body.email},
        )

    member = await repo.add_member(
        deal_room_id=room_id,
        user_id=invitee.id,
        role=body.role,
        invited_by=current_user.id,
    )
    await grant_permissions_for_new_member(
        user_id=invitee.id,
        deal_room_id=room_id,
        tenant_id=current_user.tenant_id,
        role=body.role,
        session=session,
    )
    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.MEMBER_INVITED,
        resource_type="deal_room_member",
        resource_id=invitee.id,
        resource_name=invitee.email,
        deal_room_id=room_id,
        metadata={"invited_role": body.role},
        request=request,
    )
    await session.commit()
    return member


@router.delete("/{room_id}/members/{user_id}", status_code=204)
async def remove_member(
    room_id: UUID,
    user_id: UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    repo = _repo(session, current_user)
    room = await repo.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Deal room not found")

    user_role = await repo.get_user_role(room_id, current_user.id)
    if user_role not in OWNER_ROLES:
        raise HTTPException(status_code=403, detail="Requires owner role")

    removed = await repo.remove_member(room_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found")
    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.MEMBER_REMOVED,
        resource_type="deal_room_member",
        resource_id=user_id,
        deal_room_id=room_id,
        request=request,
    )
    await session.commit()


@router.patch("/{room_id}/members/{user_id}", response_model=DealRoomMemberResponse)
async def update_member_role(
    room_id: UUID,
    user_id: UUID,
    body: UpdateMemberRoleRequest,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    repo = _repo(session, current_user)
    room = await repo.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Deal room not found")

    user_role = await repo.get_user_role(room_id, current_user.id)
    if user_role not in OWNER_ROLES:
        raise HTTPException(status_code=403, detail="Requires owner role")

    member = await repo.update_member_role(room_id, user_id, body.role)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.ROLE_CHANGED,
        resource_type="deal_room_member",
        resource_id=user_id,
        deal_room_id=room_id,
        metadata={"new_role": body.role},
        request=request,
    )
    await session.commit()
    return member
