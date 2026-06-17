"""Full analysis pipeline with streaming events at every stage."""
from __future__ import annotations

import json
from uuid import UUID

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.report import ReportItemRepository, ReportRepository
from app.services.streaming import AnalysisEvent, publish_progress

log = structlog.get_logger(__name__)


async def run_full_analysis_pipeline(
    report_id: UUID,
    deal_room_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    session: AsyncSession,
) -> None:
    """
    Research → ML scoring → Synthesis with streaming events at every stage.
    Updates the report row on completion/failure.
    """
    report_repo = ReportRepository(session, tenant_id, user_id)
    item_repo = ReportItemRepository(session)

    async def pub(evt: str, **kw):
        await publish_progress(report_id, evt, **kw)

    try:
        await report_repo.update(report_id, status="running")
        await session.commit()
        await pub(AnalysisEvent.STARTED)

        # ── Research ──────────────────────────────────────────────────────────
        await pub(AnalysisEvent.RESEARCH_START)
        target = await _get_deal_room_target(deal_room_id, session)
        from app.agents.research.agent import run_research_agent_cached
        research = await run_research_agent_cached(
            target, str(deal_room_id), str(tenant_id)
        )
        await pub(AnalysisEvent.RESEARCH_DONE, company_overview=research.get("company_overview", ""))

        # ── ML scoring ────────────────────────────────────────────────────────
        financial_chunks = await _fetch_financial_chunks(deal_room_id, tenant_id, session)
        from app.ml.features import extract_ratios_from_chunks
        ratios = await extract_ratios_from_chunks(financial_chunks)

        risk = None
        try:
            import app.ml.classifier as ml_module
            classifier = getattr(ml_module, "risk_classifier", None)
            if classifier is not None:
                risk = await classifier.predict_cached(ratios)
                await report_repo.update(
                    report_id,
                    risk_score=risk.risk_score,
                    risk_tier=risk.risk_tier,
                    risk_shap_factors=[f.model_dump() for f in risk.contributing_factors],
                )
                await session.commit()
                await pub(AnalysisEvent.ML_SCORED, risk_tier=risk.risk_tier, risk_score=risk.risk_score)
        except Exception as exc:
            log.warning("pipeline.ml_skipped", error=str(exc))

        # ── Synthesis ─────────────────────────────────────────────────────────
        await pub(AnalysisEvent.SYNTHESIS_START)
        user_role = await _get_user_deal_room_role(user_id, deal_room_id, tenant_id, session)
        from app.agents.synthesis.agent import run_synthesis
        sections, verification = await run_synthesis(
            report_id, deal_room_id, tenant_id,
            user_id, user_role, research, risk, session,
        )

        # ── Persist items ─────────────────────────────────────────────────────
        await item_repo.bulk_insert_items(report_id, tenant_id, sections)
        await report_repo.update(
            report_id,
            citation_coverage=verification.coverage_pct,
            has_unverified=bool(
                verification.uncited_item_ids or verification.hallucinated_citations
            ),
        )
        await session.commit()

        # ── Missing context ───────────────────────────────────────────────────
        missing = await generate_missing_context(deal_room_id, tenant_id, session)
        await report_repo.update(report_id, missing_context=missing, status="draft")
        await session.commit()

        log.info(
            "pipeline.complete",
            report_id=str(report_id),
            coverage=round(verification.coverage_pct, 3),
        )
        await pub(AnalysisEvent.ANALYSIS_DONE)

    except Exception as exc:
        log.exception("pipeline.failed", report_id=str(report_id), error=str(exc))
        try:
            await session.rollback()
            await report_repo.update(report_id, status="failed", error_message=str(exc))
            await session.commit()
        except Exception:
            pass
        await pub(AnalysisEvent.ANALYSIS_FAILED, error=str(exc))
        raise


async def generate_missing_context(
    deal_room_id: UUID,
    tenant_id: UUID,
    session: AsyncSession,
) -> dict:
    """Compare found doc_types against the DD checklist and identify gaps."""
    from app.agents.synthesis.prompts import DD_CHECKLIST, MISSING_CONTEXT_PROMPT
    from openai import AsyncOpenAI

    rows = await session.execute(
        text(
            "SELECT DISTINCT doc_type FROM documents "
            "WHERE deal_room_id = :dr AND tenant_id = :t AND status = 'indexed'"
        ),
        {"dr": str(deal_room_id), "t": str(tenant_id)},
    )
    found = [r[0] for r in rows if r[0]]

    missing_types = [t for t in DD_CHECKLIST if t not in found]
    if not missing_types:
        return {"missing": []}

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.CHEAP_MODEL,
        messages=[
            {
                "role": "user",
                "content": MISSING_CONTEXT_PROMPT.format(
                    found_types=", ".join(found),
                    required_types=", ".join(DD_CHECKLIST),
                ),
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=300,
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, KeyError):
        return {"missing": [{"doc_type": t, "impact": "unknown"} for t in missing_types]}


async def _get_deal_room_target(deal_room_id: UUID, session: AsyncSession) -> str:
    from app.models.deal_room import DealRoom
    row = await session.execute(
        select(DealRoom.target_company).where(DealRoom.id == deal_room_id)
    )
    return row.scalar_one_or_none() or "Unknown Company"


async def _get_user_deal_room_role(
    user_id: UUID, deal_room_id: UUID, tenant_id: UUID, session: AsyncSession
) -> str:
    from app.models.deal_room_member import DealRoomMember
    row = await session.execute(
        select(DealRoomMember.role).where(
            DealRoomMember.deal_room_id == deal_room_id,
            DealRoomMember.user_id == user_id,
            DealRoomMember.tenant_id == tenant_id,
        )
    )
    return row.scalar_one_or_none() or "analyst"


async def _fetch_financial_chunks(
    deal_room_id: UUID,
    tenant_id: UUID,
    session: AsyncSession,
) -> list[str]:
    rows = await session.execute(
        text(
            "SELECT dc.content FROM document_chunks dc "
            "JOIN documents d ON d.id = dc.document_id "
            "WHERE d.deal_room_id = :dr AND d.tenant_id = :t "
            "  AND d.doc_type = 'financial_statement' "
            "  AND dc.chunk_level = 'child' "
            "ORDER BY dc.chunk_index LIMIT 30"
        ),
        {"dr": str(deal_room_id), "t": str(tenant_id)},
    )
    return [r[0] for r in rows]
