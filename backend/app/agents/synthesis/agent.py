"""Synthesis agent — orchestrates the full RAG pipeline per section."""
from __future__ import annotations

import asyncio
import json
import uuid
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.synthesis.prompts import (
    SECTION_GROUPS,
    SECTION_QUERIES,
    SYSTEM_PROMPT,
)
from app.agents.synthesis.query_understanding import understand_query
from app.agents.synthesis.reranker import rerank
from app.agents.synthesis.retriever import advanced_retrieve
from app.agents.synthesis.verifier import VerificationResult, verify_citations
from app.core.config import settings
from app.schemas.report import SectionOutput
from app.services.streaming import AnalysisEvent, publish_progress

log = structlog.get_logger(__name__)


async def synthesize_section(
    section_type: str,
    query: str,
    chunks: list[dict],
    research_findings: dict,
    risk_assessment,
) -> list[dict]:
    """Single-section LLM call — returns list of raw item dicts."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    context = _build_context(chunks, research_findings, risk_assessment, section_type)
    schema = SectionOutput.model_json_schema()

    resp = await client.chat.completions.create(
        model=settings.CHEAP_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Section: {section_type}\n\n"
                    f"Context:\n{context}\n\n"
                    f"JSON schema:\n{json.dumps(schema, indent=2)}"
                ),
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=1500,
    )

    try:
        parsed = SectionOutput.model_validate_json(resp.choices[0].message.content)
        return [item.model_dump() for item in parsed.items]
    except Exception as exc:
        log.warning("synthesis.parse_error", section=section_type, error=str(exc))
        return []


async def run_synthesis(
    report_id: UUID,
    deal_room_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    user_role: str,
    research_findings: dict,
    risk_assessment,
    session: AsyncSession,
) -> tuple[dict[str, list], VerificationResult]:
    """
    Run all 6 section groups concurrently. Each section: understand → retrieve
    → rerank → synthesize → publish SECTION_COMPLETE event.
    Returns (all_items, verification_result).
    """
    retrieved_ids: set[str] = set()
    all_items: dict[str, list] = {}

    async def process_section(section_type: str) -> None:
        query = SECTION_QUERIES[section_type]
        plan = await understand_query(query)
        chunks = await advanced_retrieve(
            plan, deal_room_id, tenant_id, user_id, user_role, session
        )
        retrieved_ids.update(str(c["id"]) for c in chunks)
        reranked = await rerank(query, chunks, top_k=5)
        items = await synthesize_section(
            section_type, query, reranked, research_findings, risk_assessment
        )
        all_items[section_type] = items
        await publish_progress(
            report_id,
            AnalysisEvent.SECTION_COMPLETE,
            section_type=section_type,
            item_count=len(items),
        )
        log.info("synthesis.section_done", section=section_type, items=len(items))

    async def process_group(section_types: list[str]) -> None:
        await asyncio.gather(*[process_section(st) for st in section_types])

    await asyncio.gather(*[process_group(g) for g in SECTION_GROUPS])

    verification = verify_citations(all_items, retrieved_ids)
    log.info(
        "synthesis.complete",
        sections=list(all_items.keys()),
        coverage=round(verification.coverage_pct, 3),
        uncited=len(verification.uncited_item_ids),
        hallucinated=len(verification.hallucinated_citations),
    )
    return all_items, verification


def _build_context(
    chunks: list[dict],
    research_findings: dict,
    risk_assessment,
    section_type: str,
) -> str:
    parts = []

    if research_findings:
        overview = research_findings.get("company_overview", "")
        if overview:
            parts.append(f"Company Overview: {overview}")

    if risk_assessment:
        tier = getattr(risk_assessment, "risk_tier", None) or (
            risk_assessment.get("risk_tier") if isinstance(risk_assessment, dict) else None
        )
        score = getattr(risk_assessment, "risk_score", None) or (
            risk_assessment.get("risk_score") if isinstance(risk_assessment, dict) else None
        )
        if tier and score is not None:
            parts.append(f"Risk Assessment: {tier} (score: {score:.1f})")

    parts.append(f"\n--- Retrieved Document Excerpts for {section_type} ---")
    for i, chunk in enumerate(chunks, 1):
        filename = chunk.get("filename", "unknown")
        page = chunk.get("page_number", "?")
        content = chunk.get("content", "")
        parts.append(f"[{i}] {filename}, p.{page}:\n{content}")

    return "\n\n".join(parts)
