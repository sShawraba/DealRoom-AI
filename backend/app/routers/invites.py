"""Public invite endpoints — validate token and accept invitation."""
from __future__ import annotations

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.audit import AuditAction, log_event
from app.core.config import settings
from app.core.deps import SessionDep
from app.core.security import create_access_token, hash_password
from app.models.deal_room import DealRoom
from app.models.deal_room_member import DealRoomMember
from app.models.invite_token import InviteToken
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.invite import InviteAcceptRequest, InviteInfoResponse
from app.services.document_service import grant_permissions_for_new_member

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/invites", tags=["invites"])


async def _get_valid_token(token: str, session) -> InviteToken:
    """Fetch and validate an invite token — raises 404/410 on failure."""
    invite = (
        await session.execute(
            select(InviteToken).where(InviteToken.token == token)
        )
    ).scalar_one_or_none()

    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.used_at is not None:
        raise HTTPException(status_code=410, detail="Invite already used")
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invite has expired")
    return invite


@router.get("/{token}", response_model=InviteInfoResponse)
async def get_invite_info(token: str, session: SessionDep):
    """Return invite metadata so the frontend can pre-fill the accept form."""
    invite = await _get_valid_token(token, session)

    inviter = (
        await session.execute(select(User).where(User.id == invite.invited_by_id))
    ).scalar_one_or_none()

    deal_room_name: str | None = None
    if invite.deal_room_id:
        room = (
            await session.execute(select(DealRoom).where(DealRoom.id == invite.deal_room_id))
        ).scalar_one_or_none()
        if room:
            deal_room_name = room.name

    return InviteInfoResponse(
        email=invite.email,
        invited_by_name=inviter.full_name if inviter else "A team member",
        deal_room_name=deal_room_name,
        deal_room_role=invite.deal_room_role,
    )


@router.post("/{token}/accept", response_model=TokenResponse, status_code=201)
async def accept_invite(token: str, body: InviteAcceptRequest, request: Request, session: SessionDep):
    """Create the user account and add them to the deal room, then return a JWT."""
    invite = await _get_valid_token(token, session)

    existing = (
        await session.execute(select(User).where(User.email == invite.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists. Please log in.")

    user = User(
        tenant_id=invite.tenant_id,
        email=invite.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role="analyst",
    )
    session.add(user)
    await session.flush()

    if invite.deal_room_id and invite.deal_room_role:
        member = DealRoomMember(
            tenant_id=invite.tenant_id,
            deal_room_id=invite.deal_room_id,
            user_id=user.id,
            role=invite.deal_room_role,
            invited_by=invite.invited_by_id,
        )
        session.add(member)
        await session.flush()
        await grant_permissions_for_new_member(
            user_id=user.id,
            deal_room_id=invite.deal_room_id,
            tenant_id=invite.tenant_id,
            role=invite.deal_room_role,
            session=session,
        )

    invite.used_at = datetime.now(timezone.utc)

    await log_event(
        session=session,
        actor_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        tenant_id=invite.tenant_id,
        action=AuditAction.INVITE_ACCEPTED,
        resource_type="user",
        resource_id=user.id,
        resource_name=user.email,
        request=request,
        metadata={"invited_by": str(invite.invited_by_id), "deal_room_id": str(invite.deal_room_id) if invite.deal_room_id else None},
    )

    await session.commit()
    log.info("invite.accepted", email=user.email, tenant_id=str(invite.tenant_id))

    jwt = create_access_token(user.id, invite.tenant_id, user.role, user.email, user.full_name)
    return TokenResponse(access_token=jwt)
