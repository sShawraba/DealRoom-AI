from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.core.audit import AuditAction, log_event
from app.core.deps import CurrentUser, CurrentUserDep, SessionDep
from app.models.user import User
from app.repositories.deal_room import DealRoomRepository
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
    repo = _repo(session, current_user)
    items, total = await repo.list_all(page=page, page_size=page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=DealRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_deal_room(
    body: DealRoomCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
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
    start = (page - 1) * page_size
    page_items = all_members[start: start + page_size]
    return PaginatedResponse(
        items=page_items,
        total=len(all_members),
        page=page,
        page_size=page_size,
    )


@router.post("/{room_id}/members", response_model=DealRoomMemberResponse, status_code=201)
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
        raise HTTPException(status_code=404, detail="User not found in this workspace")

    member = await repo.add_member(
        deal_room_id=room_id,
        user_id=invitee.id,
        role=body.role,
        invited_by=current_user.id,
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
