"""Stage 2–3 — Parallel retrieval (pgvector + BM25) + RRF fusion."""
from __future__ import annotations

import asyncio
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.synthesis.query_understanding import QueryPlan

log = structlog.get_logger(__name__)

_PGVECTOR_QUERY = text("""
    SELECT dc.id, dc.content, dc.page_number, dc.chunk_level,
           dc.parent_chunk_id, dc.section_header, d.filename, d.doc_type,
           1 - (dc.embedding <=> cast(:emb AS vector)) AS similarity
    FROM document_chunks dc
    JOIN documents d ON d.id = dc.document_id
    JOIN document_permissions dp ON dp.document_id = d.id
    WHERE dc.tenant_id    = :tenant_id
      AND dc.deal_room_id = :deal_room_id
      AND dc.chunk_level  = 'child'
      AND dp.can_view     = TRUE
      AND (dp.user_id = :user_id OR dp.role = :user_role)
      AND (:doc_types IS NULL OR d.doc_type = ANY(:doc_types))
    ORDER BY dc.embedding <=> cast(:emb AS vector)
    LIMIT 10
""")

_BM25_CONTENT_QUERY = text("""
    SELECT dc.id, dc.content, dc.page_number, dc.chunk_level,
           dc.parent_chunk_id, dc.section_header, d.filename, d.doc_type
    FROM document_chunks dc
    JOIN documents d ON d.id = dc.document_id
    JOIN document_permissions dp ON dp.document_id = d.id
    WHERE dc.tenant_id    = :tenant_id
      AND dc.deal_room_id = :deal_room_id
      AND dc.chunk_level  = 'child'
      AND dp.can_view     = TRUE
      AND (dp.user_id = :user_id OR dp.role = :user_role)
    LIMIT 200
""")

_PARENT_FETCH_QUERY = text("""
    SELECT id, content, page_number, section_header, document_id
    FROM document_chunks
    WHERE id = ANY(:ids)
""")


async def advanced_retrieve(
    query_plan: QueryPlan,
    deal_room_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    user_role: str,
    session: AsyncSession,
    final_top_k: int = 20,
) -> list[dict]:
    from app.agents.ingestion.agent import get_embeddings_batch_cached

    all_queries = [query_plan.original] + query_plan.variants
    all_embeddings = await get_embeddings_batch_cached(all_queries)
    all_embeddings.append(query_plan.hyde_embedding)

    doc_types = query_plan.doc_type_filter or None

    pgvector_tasks = [
        _run_pgvector(emb, deal_room_id, tenant_id, user_id, user_role, doc_types, session)
        for emb in all_embeddings
    ]
    bm25_tasks = [
        _run_bm25(q, deal_room_id, tenant_id, user_id, user_role, session)
        for q in all_queries
    ]

    all_result_sets = await asyncio.gather(*pgvector_tasks, *bm25_tasks)

    fused = _reciprocal_rank_fusion(list(all_result_sets), k=60)
    top_n = fused[:final_top_k]

    result = await _fetch_parent_chunks(top_n, session)
    log.info(
        "retriever.done",
        query_preview=query_plan.original[:60],
        fused=len(fused),
        returned=len(result),
    )
    return result


async def _run_pgvector(
    emb: list[float],
    deal_room_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    user_role: str,
    doc_types: list[str] | None,
    session: AsyncSession,
) -> list[dict]:
    import json as _json
    emb_str = "[" + ",".join(str(v) for v in emb) + "]"
    rows = await session.execute(
        _PGVECTOR_QUERY,
        {
            "emb": emb_str,
            "tenant_id": str(tenant_id),
            "deal_room_id": str(deal_room_id),
            "user_id": str(user_id),
            "user_role": user_role,
            "doc_types": doc_types,
        },
    )
    return [dict(row._mapping) for row in rows]


async def _run_bm25(
    query: str,
    deal_room_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    user_role: str,
    session: AsyncSession,
) -> list[dict]:
    from rank_bm25 import BM25Okapi

    rows = await session.execute(
        _BM25_CONTENT_QUERY,
        {
            "tenant_id": str(tenant_id),
            "deal_room_id": str(deal_room_id),
            "user_id": str(user_id),
            "user_role": user_role,
        },
    )
    candidates = [dict(row._mapping) for row in rows]
    if not candidates:
        return []

    tokenized_corpus = [c["content"].lower().split() for c in candidates]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(query.lower().split())

    scored = sorted(
        zip(scores, candidates), key=lambda x: x[0], reverse=True
    )
    return [c for _, c in scored[:10]]


def _reciprocal_rank_fusion(result_sets: list[list[dict]], k: int = 60) -> list[dict]:
    scores: dict[str, float] = {}
    chunks: dict[str, dict] = {}
    for rs in result_sets:
        for rank, chunk in enumerate(rs):
            cid = str(chunk["id"])
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            chunks[cid] = chunk
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [chunks[cid] for cid, _ in ranked]


async def _fetch_parent_chunks(
    child_chunks: list[dict],
    session: AsyncSession,
) -> list[dict]:
    """Replace child chunks with their parent chunks for richer context."""
    parent_ids = [
        str(c["parent_chunk_id"])
        for c in child_chunks
        if c.get("parent_chunk_id")
    ]
    if not parent_ids:
        return child_chunks

    rows = await session.execute(_PARENT_FETCH_QUERY, {"ids": parent_ids})
    parent_map = {str(row.id): dict(row._mapping) for row in rows}

    result = []
    for chunk in child_chunks:
        pid = str(chunk.get("parent_chunk_id") or "")
        if pid and pid in parent_map:
            parent = dict(parent_map[pid])
            parent["id"] = chunk["id"]
            parent["filename"] = chunk.get("filename")
            parent["doc_type"] = chunk.get("doc_type")
            result.append(parent)
        else:
            result.append(chunk)
    return result
