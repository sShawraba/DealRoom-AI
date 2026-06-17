"""ARQ background tasks for document ingestion and report analysis."""
from __future__ import annotations

import structlog

log = structlog.get_logger(__name__)


async def task_ingest_document(
    ctx: dict, document_id: str, deal_room_id: str, tenant_id: str
) -> None:
    """ARQ task: ingest a document through the full pipeline."""
    from uuid import UUID
    from app.core.database import AsyncSessionLocal
    from app.agents.ingestion.agent import run_ingestion

    log.info(
        "task.ingest_document.start",
        document_id=document_id,
        deal_room_id=deal_room_id,
    )

    async with AsyncSessionLocal() as session:
        await run_ingestion(
            document_id=UUID(document_id),
            deal_room_id=UUID(deal_room_id),
            tenant_id=UUID(tenant_id),
            session=session,
        )

    log.info("task.ingest_document.done", document_id=document_id)


async def task_run_analysis(
    ctx: dict,
    report_id: str,
    deal_room_id: str,
    tenant_id: str,
    user_id: str,
) -> None:
    """ARQ task: run the full analysis pipeline for a report."""
    from uuid import UUID
    from app.core.database import AsyncSessionLocal
    from app.services.report_service import run_full_analysis_pipeline

    log.info(
        "task.run_analysis.start",
        report_id=report_id,
        deal_room_id=deal_room_id,
    )

    async with AsyncSessionLocal() as session:
        await run_full_analysis_pipeline(
            report_id=UUID(report_id),
            deal_room_id=UUID(deal_room_id),
            tenant_id=UUID(tenant_id),
            user_id=UUID(user_id),
            session=session,
        )

    log.info("task.run_analysis.done", report_id=report_id)
