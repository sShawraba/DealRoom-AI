"""Comparison and precedent-search endpoints for Phase 7."""
from __future__ import annotations

import uuid
from typing import Optional  # noqa: F401 (used in query params)

import structlog
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, text

from app.core.deps import CurrentUser, CurrentUserDep, SessionDep
from app.repositories.deal_room import DealRoomRepository
from app.repositories.report import ReportItemRepository, ReportRepository
from app.schemas.comparison import CompareResponse, DealRoomComparisonItem, DealRoomSearchResult
from app.schemas.pagination import PaginatedResponse

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/deal-rooms", tags=["comparison"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _repo(session, current_user: CurrentUser) -> DealRoomRepository:
    return DealRoomRepository(session, current_user.tenant_id, current_user.id)


def _report_repo(session, current_user: CurrentUser) -> ReportRepository:
    return ReportRepository(session, current_user.tenant_id, current_user.id)


async def _build_comparison_item(
    room,
    report,
    item_repo: ReportItemRepository,
) -> DealRoomComparisonItem:
    if report is None:
        return DealRoomComparisonItem(
            id=room.id,
            name=room.name,
            target_company=room.target_company,
            risk_score=room.risk_score,
            risk_tier=room.risk_tier,
            red_flag_count=0,
            financial_snapshot=[],
            top_findings=[],
        )

    items = await item_repo.get_items_for_report(report.id)

    red_flag_count = sum(1 for i in items if i.section_type == "red_flags")
    top_findings = [
        i.content for i in items if i.section_type == "executive_summary"
    ][:3]
    financial_snapshot = [
        i.content for i in items if i.section_type == "financial_health"
    ][:5]

    return DealRoomComparisonItem(
        id=room.id,
        name=room.name,
        target_company=room.target_company,
        risk_score=report.risk_score,
        risk_tier=report.risk_tier,
        red_flag_count=red_flag_count,
        financial_snapshot=financial_snapshot,
        top_findings=top_findings,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/compare", response_model=CompareResponse)
async def compare_deal_rooms(
    session: SessionDep,
    current_user: CurrentUserDep,
    ids: str = Query(..., description="Comma-separated pair of deal room UUIDs"),
):
    """Side-by-side comparison of two deal rooms. Caller must be a member of both."""
    parts = [p.strip() for p in ids.split(",")]
    if len(parts) != 2:
        raise HTTPException(status_code=422, detail="Exactly two deal room IDs required")

    try:
        id_list = [uuid.UUID(p) for p in parts]
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID in ids parameter")

    repo = _repo(session, current_user)
    report_repo = _report_repo(session, current_user)
    item_repo = ReportItemRepository(session)

    rooms = []
    for room_id in id_list:
        room = await repo.get_by_id(room_id)
        if room is None:
            raise HTTPException(status_code=404, detail=f"Deal room {room_id} not found")
        rooms.append(room)

    items = []
    for room in rooms:
        report = await report_repo.get_latest_approved(room.id)
        item = await _build_comparison_item(room, report, item_repo)
        items.append(item)

    return CompareResponse(deal_rooms=items)


def _build_search_queries(status: Optional[str]):
    status_clause = "AND dr.status = :status" if status is not None else ""
    search_sql = text(f"""
        SELECT
            dc.deal_room_id,
            dr.name,
            dr.target_company,
            dr.status,
            dr.risk_tier,
            MAX(1 - (dc.embedding <=> cast(:emb AS vector))) AS match_score
        FROM document_chunks dc
        JOIN deal_rooms dr ON dr.id = dc.deal_room_id
        WHERE dc.tenant_id = :tenant_id
          AND dc.embedding IS NOT NULL
          {status_clause}
        GROUP BY dc.deal_room_id, dr.name, dr.target_company, dr.status, dr.risk_tier
        ORDER BY match_score DESC
        LIMIT :limit OFFSET :offset
    """)
    count_sql = text(f"""
        SELECT COUNT(DISTINCT dc.deal_room_id)
        FROM document_chunks dc
        JOIN deal_rooms dr ON dr.id = dc.deal_room_id
        WHERE dc.tenant_id = :tenant_id
          AND dc.embedding IS NOT NULL
          {status_clause}
    """)
    return search_sql, count_sql


@router.get("/search", response_model=PaginatedResponse[DealRoomSearchResult])
async def search_deal_rooms(
    session: SessionDep,
    current_user: CurrentUserDep,
    q: str = Query(..., min_length=1, description="Natural language search query"),
    status: Optional[str] = Query(None, description="Filter by deal room status, e.g. closed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """Semantic search over past deals within the tenant using pgvector."""
    from app.agents.ingestion.agent import get_embeddings_batch_cached

    embeddings = await get_embeddings_batch_cached([q])
    query_emb = embeddings[0]

    offset = (page - 1) * page_size
    emb_str = "[" + ",".join(str(v) for v in query_emb) + "]"

    search_sql, count_sql = _build_search_queries(status)
    params: dict = {"emb": emb_str, "tenant_id": current_user.tenant_id, "limit": page_size, "offset": offset}
    count_params: dict = {"tenant_id": current_user.tenant_id}
    if status is not None:
        params["status"] = status
        count_params["status"] = status

    rows = (await session.execute(search_sql, params)).fetchall()
    total_row = (await session.execute(count_sql, count_params)).scalar_one()

    results = [
        DealRoomSearchResult(
            id=row.deal_room_id,
            name=row.name,
            target_company=row.target_company,
            risk_tier=row.risk_tier,
            match_score=float(row.match_score),
        )
        for row in rows
    ]

    return PaginatedResponse(
        items=results,
        total=int(total_row),
        page=page,
        page_size=page_size,
    )
