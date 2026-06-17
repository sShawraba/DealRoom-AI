"""Report creation, listing, and detail endpoints."""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.audit import AuditAction, log_event
from app.core.deps import CurrentUserDep, SessionDep
from app.core.redis import get_arq_pool
from app.models.document import Document
from app.models.report import Report
from app.repositories.deal_room import DealRoomRepository
from app.repositories.report import ReportItemRepository, ReportRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.report import ReportResponse, ReportSummary

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

    from app.schemas.report import ReportItemResponse
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
        items=[ReportItemResponse.model_validate(i) for i in items],
        created_at=report.created_at,
        updated_at=report.updated_at,
    )
