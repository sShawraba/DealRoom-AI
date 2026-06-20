"""Report creation, listing, detail, item edit and approval status endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.audit import AuditAction, log_event
from app.core.deps import CurrentUserDep, SessionDep
from app.core.guardrails import moderate_content
from app.core.redis import get_arq_pool
from app.models.document import Document
from app.models.report import Report, ReportItem
from app.models.user import User
from app.repositories.deal_room import DealRoomRepository
from app.repositories.report import ReportItemRepository, ReportRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.report import (
    ReportItemEditBody,
    ReportItemResponse,
    ReportResponse,
    ReportStatusBody,
    ReportSummary,
)

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/deal-rooms/{deal_room_id}/reports",
    tags=["reports"],
)


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    deal_room_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ReportResponse:
    """
    Trigger a new analysis report for a deal room.
    Validates that at least one document is indexed before enqueuing.
    """
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    deal_room = await dr_repo.get_by_id(deal_room_id)
    if deal_room is None:
        raise HTTPException(status_code=404, detail="Deal room not found")

    # Require at least one indexed document
    indexed = await session.execute(
        select(Document).where(
            Document.deal_room_id == deal_room_id,
            Document.tenant_id == current_user.tenant_id,
            Document.status == "indexed",
        ).limit(1)
    )
    if indexed.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No indexed documents in this deal room. Upload and index documents first.",
        )

    report_repo = ReportRepository(session, current_user.tenant_id, current_user.id)
    report = await report_repo.create(
        deal_room_id=deal_room_id,
        created_by=current_user.id,
    )

    arq = await get_arq_pool()
    job = await arq.enqueue_job(
        "task_run_analysis",
        str(report.id),
        str(deal_room_id),
        str(current_user.tenant_id),
        str(current_user.id),
    )
    if job:
        report.arq_job_id = job.job_id
        await session.flush()

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.ANALYSIS_STARTED,
        resource_type="report",
        resource_id=report.id,
        resource_name=f"report:{report.id}",
        deal_room_id=deal_room_id,
        metadata={"arq_job_id": report.arq_job_id},
        request=request,
    )
    await session.commit()

    return ReportResponse(
        id=report.id,
        deal_room_id=report.deal_room_id,
        created_by=report.created_by,
        status=report.status,
        risk_score=report.risk_score,
        risk_tier=report.risk_tier,
        risk_shap_factors=report.risk_shap_factors,
        citation_coverage=report.citation_coverage,
        has_unverified=report.has_unverified,
        missing_context=report.missing_context,
        error_message=report.error_message,
        items=[],
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.get("", response_model=PaginatedResponse[ReportSummary])
async def list_reports(
    deal_room_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[ReportSummary]:
    """List reports for a deal room (paginated, newest first)."""
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    if await dr_repo.get_by_id(deal_room_id) is None:
        raise HTTPException(status_code=404, detail="Deal room not found")

    report_repo = ReportRepository(session, current_user.tenant_id, current_user.id)
    reports, total = await report_repo.list_for_deal_room(
        deal_room_id=deal_room_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[ReportSummary.model_validate(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    deal_room_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ReportResponse:
    """Get a full report including all section items."""
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    if await dr_repo.get_by_id(deal_room_id) is None:
        raise HTTPException(status_code=404, detail="Deal room not found")

    report_repo = ReportRepository(session, current_user.tenant_id, current_user.id)
    report = await report_repo.get_by_id(report_id)
    if report is None or report.deal_room_id != deal_room_id:
        raise HTTPException(status_code=404, detail="Report not found")

    item_repo = ReportItemRepository(session)
    items = await item_repo.get_items_for_report(report_id)

    # Batch-load editor names for items that have been edited
    editor_ids = list({i.edited_by for i in items if i.edited_by})
    editor_map: dict[uuid.UUID, str] = {}
    if editor_ids:
        user_rows = (await session.execute(
            select(User).where(User.id.in_(editor_ids))
        )).scalars().all()
        editor_map = {u.id: u.email for u in user_rows}

    return ReportResponse(
        id=report.id,
        deal_room_id=report.deal_room_id,
        created_by=report.created_by,
        status=report.status,
        risk_score=report.risk_score,
        risk_tier=report.risk_tier,
        risk_shap_factors=report.risk_shap_factors,
        citation_coverage=report.citation_coverage,
        has_unverified=report.has_unverified,
        missing_context=report.missing_context,
        error_message=report.error_message,
        items=[
            ReportItemResponse(
                id=i.id,
                section_type=i.section_type,
                content=i.content,
                citation=i.citation,
                is_verified=i.is_verified,
                item_index=i.item_index,
                edited_content=i.edited_content,
                edited_by=i.edited_by,
                edited_by_email=editor_map.get(i.edited_by) if i.edited_by else None,
                edited_at=i.edited_at,
                created_at=i.created_at,
            )
            for i in items
        ],
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


# ── PATCH /{report_id}/items/{item_id} ───────────────────────────────────────

@router.patch("/{report_id}/items/{item_id}", response_model=ReportItemResponse)
async def edit_report_item(
    deal_room_id: uuid.UUID,
    report_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ReportItemEditBody,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ReportItemResponse:
    """Senior analyst edits an item's content (original AI content preserved)."""
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    if await dr_repo.get_by_id(deal_room_id) is None:
        raise HTTPException(404, "Deal room not found")

    report_repo = ReportRepository(session, current_user.tenant_id, current_user.id)
    report = await report_repo.get_by_id(report_id)
    if report is None or report.deal_room_id != deal_room_id:
        raise HTTPException(404, "Report not found")
    if report.status == "approved":
        raise HTTPException(409, "Report is approved and read-only")

    result = await session.execute(
        select(ReportItem).where(
            ReportItem.id == item_id,
            ReportItem.report_id == report_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(404, "Report item not found")

    item.edited_content = body.edited_content
    item.edited_by = current_user.id
    item.edited_at = datetime.now(timezone.utc)
    await session.flush()

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.REPORT_ITEM_EDITED,
        resource_type="report_item",
        resource_id=item_id,
        resource_name=f"report_item:{item_id}",
        deal_room_id=deal_room_id,
        metadata={"report_id": str(report_id)},
        request=request,
    )
    await session.commit()
    await session.refresh(item)
    return ReportItemResponse(
        id=item.id,
        section_type=item.section_type,
        content=item.content,
        citation=item.citation,
        is_verified=item.is_verified,
        item_index=item.item_index,
        edited_content=item.edited_content,
        edited_by=item.edited_by,
        edited_by_email=current_user.email,
        edited_at=item.edited_at,
        created_at=item.created_at,
    )


# ── POST /{report_id}/status ──────────────────────────────────────────────────

@router.post("/{report_id}/status", response_model=dict)
async def update_report_status(
    deal_room_id: uuid.UUID,
    report_id: uuid.UUID,
    body: ReportStatusBody,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """Submit for review or approve a report."""
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    if await dr_repo.get_by_id(deal_room_id) is None:
        raise HTTPException(404, "Deal room not found")

    report_repo = ReportRepository(session, current_user.tenant_id, current_user.id)
    report = await report_repo.get_by_id(report_id)
    if report is None or report.deal_room_id != deal_room_id:
        raise HTTPException(404, "Report not found")

    if body.action == "submit_for_review":
        if report.status not in ("draft",):
            raise HTTPException(409, f"Cannot submit report in status '{report.status}'")
        report.status = "in_review"
        await session.flush()
        await log_event(
            session=session,
            actor_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            tenant_id=current_user.tenant_id,
            action=AuditAction.REPORT_SUBMITTED,
            resource_type="report",
            resource_id=report_id,
            deal_room_id=deal_room_id,
            request=request,
        )
        await session.commit()
        return {"status": "in_review"}

    elif body.action == "approve":
        if report.status != "in_review":
            raise HTTPException(409, f"Cannot approve report in status '{report.status}'")

        from app.services.approval_service import assert_can_approve, approve_report

        if body.sign_off_notes:
            moderation = await moderate_content(body.sign_off_notes)
            if moderation.flagged:
                await log_event(
                    session=session,
                    actor_id=current_user.id,
                    actor_email=current_user.email,
                    actor_role=current_user.role,
                    tenant_id=current_user.tenant_id,
                    action=AuditAction.GUARDRAIL_CONTENT_FLAGGED,
                    resource_type="report",
                    resource_id=report_id,
                    metadata={"categories": moderation.categories},
                    request=request,
                )
                await session.commit()
                raise HTTPException(422, f"Content flagged: {moderation.categories}")

        await assert_can_approve(
            deal_room_id=deal_room_id,
            report_id=report_id,
            current_user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            session=session,
        )
        approval = await approve_report(
            report=report,
            approved_by=current_user.id,
            tenant_id=current_user.tenant_id,
            session=session,
            sign_off_notes=body.sign_off_notes,
        )
        await log_event(
            session=session,
            actor_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            tenant_id=current_user.tenant_id,
            action=AuditAction.REPORT_APPROVED,
            resource_type="report",
            resource_id=report_id,
            deal_room_id=deal_room_id,
            metadata={"approval_id": str(approval.id)},
            request=request,
        )
        await session.commit()
        return {"status": "approved", "approval_id": str(approval.id)}

    else:
        raise HTTPException(400, f"Unknown action: {body.action}")


# ── POST /{report_id}/cancel ──────────────────────────────────────────────────

@router.post("/{report_id}/cancel", response_model=dict)
async def cancel_report(
    deal_room_id: uuid.UUID,
    report_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """Cancel a pending or running report and abort its ARQ job."""
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    if await dr_repo.get_by_id(deal_room_id) is None:
        raise HTTPException(404, "Deal room not found")

    report_repo = ReportRepository(session, current_user.tenant_id, current_user.id)
    report = await report_repo.get_by_id(report_id)
    if report is None or report.deal_room_id != deal_room_id:
        raise HTTPException(404, "Report not found")

    if report.status not in ("pending", "running"):
        raise HTTPException(409, f"Cannot cancel report in status '{report.status}'")

    # Best-effort abort the ARQ job
    if report.arq_job_id:
        try:
            from arq.jobs import Job
            arq_pool = await get_arq_pool()
            job = Job(report.arq_job_id, arq_pool)
            await job.abort(timeout=2)
        except Exception as exc:
            log.warning("report.cancel_abort_failed", job_id=report.arq_job_id, error=str(exc))

    report.status = "failed"
    report.error_message = "Cancelled by user"
    await session.flush()
    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.REPORT_SUBMITTED,
        resource_type="report",
        resource_id=report_id,
        deal_room_id=deal_room_id,
        metadata={"cancelled": True},
        request=request,
    )
    await session.commit()
    log.info("report.cancelled", report_id=str(report_id), user=str(current_user.id))
    return {"status": "failed", "message": "Cancelled"}
