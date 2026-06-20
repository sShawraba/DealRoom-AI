"""Annotation endpoints — create, list, patch, reply."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.audit import AuditAction, log_event
from app.core.deps import CurrentUserDep, SessionDep
from app.core.guardrails import moderate_content
from app.models.annotation import Annotation, AnnotationReply
from app.models.user import User
from app.repositories.annotation import AnnotationRepository
from app.repositories.deal_room import DealRoomRepository
from app.schemas.annotation import (
    AnnotationCreate,
    AnnotationPatch,
    AnnotationReplyCreate,
    AnnotationReplyResponse,
    AnnotationResponse,
    AnnotationsByItemResponse,
)

log = structlog.get_logger(__name__)

router = APIRouter(tags=["annotations"])

# ── POST /api/v1/deal-rooms/{id}/annotations ─────────────────────────────────

_deal_room_router = APIRouter(
    prefix="/api/v1/deal-rooms/{deal_room_id}",
    tags=["annotations"],
)


@_deal_room_router.post(
    "/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation(
    deal_room_id: uuid.UUID,
    body: AnnotationCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AnnotationResponse:
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    if await dr_repo.get_by_id(deal_room_id) is None:
        raise HTTPException(404, "Deal room not found")

    moderation = await moderate_content(body.content)
    if moderation.flagged:
        await log_event(
            session=session,
            actor_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            tenant_id=current_user.tenant_id,
            action=AuditAction.GUARDRAIL_CONTENT_FLAGGED,
            resource_type="annotation",
            deal_room_id=deal_room_id,
            metadata={"categories": moderation.categories, "user_id": str(current_user.id)},
            request=request,
        )
        await session.commit()
        raise HTTPException(422, f"Content flagged: {moderation.categories}")

    ann_repo = AnnotationRepository(session, current_user.tenant_id)
    annotation = await ann_repo.create(
        deal_room_id=deal_room_id,
        report_item_id=body.report_item_id,
        author_id=current_user.id,
        content=body.content,
        annotation_type=body.type,
    )

    action = (
        AuditAction.ANNOTATION_DISPUTED
        if body.type == "disputed"
        else AuditAction.ANNOTATION_CREATED
    )
    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=action,
        resource_type="annotation",
        resource_id=annotation.id,
        resource_name=f"annotation:{annotation.id}",
        deal_room_id=deal_room_id,
        metadata={"type": body.type, "report_item_id": str(body.report_item_id)},
        request=request,
    )
    await session.commit()
    return AnnotationResponse(
        id=annotation.id,
        deal_room_id=annotation.deal_room_id,
        report_item_id=annotation.report_item_id,
        author_id=annotation.author_id,
        author_email=current_user.email,
        author_name=current_user.full_name,
        content=annotation.content,
        type=annotation.type,
        resolved=annotation.resolved,
        resolved_by=annotation.resolved_by,
        resolved_at=annotation.resolved_at,
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
        replies=[],
    )


@_deal_room_router.get(
    "/annotations",
    response_model=AnnotationsByItemResponse,
)
async def list_annotations(
    deal_room_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = 1,
    page_size: int = 50,
) -> AnnotationsByItemResponse:
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    if await dr_repo.get_by_id(deal_room_id) is None:
        raise HTTPException(404, "Deal room not found")

    ann_repo = AnnotationRepository(session, current_user.tenant_id)
    grouped, total = await ann_repo.list_by_deal_room(
        deal_room_id=deal_room_id, page=page, page_size=page_size
    )

    all_anns = [a for anns in grouped.values() for a in anns]

    # Batch-load authors for all annotations
    author_ids = list({a.author_id for a in all_anns})
    user_map: dict[uuid.UUID, User] = {}
    if author_ids:
        rows = (await session.execute(
            select(User).where(User.id.in_(author_ids))
        )).scalars().all()
        user_map = {u.id: u for u in rows}

    # Load replies with their authors in one query
    ann_ids = [a.id for a in all_anns]
    replies_by_ann: dict[uuid.UUID, list[AnnotationReplyResponse]] = {}
    if ann_ids:
        from sqlalchemy.orm import aliased
        ReplyAuthor = aliased(User)
        reply_rows = (await session.execute(
            select(AnnotationReply, ReplyAuthor.email, ReplyAuthor.full_name)
            .join(ReplyAuthor, ReplyAuthor.id == AnnotationReply.author_id)
            .where(
                AnnotationReply.annotation_id.in_(ann_ids),
                AnnotationReply.tenant_id == current_user.tenant_id,
            )
            .order_by(AnnotationReply.created_at)
        )).all()

        for reply, r_email, r_name in reply_rows:
            replies_by_ann.setdefault(reply.annotation_id, []).append(
                AnnotationReplyResponse(
                    id=reply.id,
                    annotation_id=reply.annotation_id,
                    author_id=reply.author_id,
                    author_email=r_email,
                    author_name=r_name,
                    content=reply.content,
                    created_at=reply.created_at,
                )
            )

    serialized: dict[str, list[AnnotationResponse]] = {}
    for item_id, anns in grouped.items():
        serialized[item_id] = [
            AnnotationResponse(
                id=a.id,
                deal_room_id=a.deal_room_id,
                report_item_id=a.report_item_id,
                author_id=a.author_id,
                author_email=user_map[a.author_id].email if a.author_id in user_map else None,
                author_name=user_map[a.author_id].full_name if a.author_id in user_map else None,
                content=a.content,
                type=a.type,
                resolved=a.resolved,
                resolved_by=a.resolved_by,
                resolved_at=a.resolved_at,
                created_at=a.created_at,
                updated_at=a.updated_at,
                replies=replies_by_ann.get(a.id, []),
            )
            for a in anns
        ]

    return AnnotationsByItemResponse(
        annotations=serialized, total=total, page=page, page_size=page_size
    )


# ── PATCH /api/v1/annotations/{id} ───────────────────────────────────────────

_annotation_router = APIRouter(
    prefix="/api/v1/annotations",
    tags=["annotations"],
)


@_annotation_router.patch("/{annotation_id}", response_model=AnnotationResponse)
async def patch_annotation(
    annotation_id: uuid.UUID,
    body: AnnotationPatch,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AnnotationResponse:
    ann_repo = AnnotationRepository(session, current_user.tenant_id)
    annotation = await ann_repo.get_by_id(annotation_id)
    if annotation is None:
        raise HTTPException(404, "Annotation not found")

    kwargs: dict = {}
    if body.type is not None:
        kwargs["type"] = body.type
    if body.resolved is True:
        kwargs["resolved"] = True
        kwargs["resolved_by"] = current_user.id
        kwargs["resolved_at"] = datetime.now(timezone.utc)

    annotation = await ann_repo.patch(annotation_id, **kwargs)

    if body.resolved:
        await log_event(
            session=session,
            actor_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            tenant_id=current_user.tenant_id,
            action=AuditAction.ANNOTATION_RESOLVED,
            resource_type="annotation",
            resource_id=annotation_id,
            resource_name=f"annotation:{annotation_id}",
            deal_room_id=annotation.deal_room_id,
            request=request,
        )
    await session.commit()
    return AnnotationResponse.model_validate(annotation)


@_annotation_router.post(
    "/{annotation_id}/replies",
    response_model=AnnotationReplyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reply(
    annotation_id: uuid.UUID,
    body: AnnotationReplyCreate,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AnnotationReplyResponse:
    ann_repo = AnnotationRepository(session, current_user.tenant_id)
    if await ann_repo.get_by_id(annotation_id) is None:
        raise HTTPException(404, "Annotation not found")

    moderation = await moderate_content(body.content)
    if moderation.flagged:
        await log_event(
            session=session,
            actor_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            tenant_id=current_user.tenant_id,
            action=AuditAction.GUARDRAIL_CONTENT_FLAGGED,
            resource_type="annotation_reply",
            metadata={"categories": moderation.categories, "user_id": str(current_user.id)},
            request=request,
        )
        await session.commit()
        raise HTTPException(422, f"Content flagged: {moderation.categories}")

    reply = await ann_repo.create_reply(
        annotation_id=annotation_id,
        author_id=current_user.id,
        content=body.content,
    )
    await session.commit()
    return AnnotationReplyResponse(
        id=reply.id,
        annotation_id=reply.annotation_id,
        author_id=reply.author_id,
        author_email=current_user.email,
        author_name=current_user.full_name,
        content=reply.content,
        created_at=reply.created_at,
    )
