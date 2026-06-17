"""Stage 1 — Query Understanding: multi-query, HyDE embedding, routing."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import structlog
from openai import AsyncOpenAI

from app.agents.ingestion.agent import get_embeddings_batch_cached
from app.core.config import settings

log = structlog.get_logger(__name__)


@dataclass
class QueryPlan:
    original: str
    variants: list[str] = field(default_factory=list)
    hyde_embedding: list[float] = field(default_factory=list)
    doc_type_filter: list[str] = field(default_factory=list)


async def understand_query(query: str) -> QueryPlan:
    """Multi-query + HyDE + routing all concurrently."""
    variants, hyde_emb, doc_types = await asyncio.gather(
        _generate_variants(query, n=3),
        _generate_hyde_embedding(query),
        _route_query(query),
    )
    log.info(
        "query_understanding.done",
        query_preview=query[:60],
        variants=len(variants),
        doc_types=doc_types,
    )
    return QueryPlan(
        original=query,
        variants=variants,
        hyde_embedding=hyde_emb,
        doc_type_filter=doc_types,
    )


async def _generate_variants(query: str, n: int = 3) -> list[str]:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.CHEAP_MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Generate {n} different search queries to find information about: {query}\n"
                    f"Use different vocabulary and phrasings. "
                    f'Return ONLY valid JSON: {{"queries": ["...", "...", "..."]}}'
                ),
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=200,
    )
    try:
        data = json.loads(resp.choices[0].message.content)
        variants = data.get("queries", [])
        return [v for v in variants if isinstance(v, str) and v.strip()][:n] or [query]
    except (json.JSONDecodeError, KeyError):
        return [query]


async def _generate_hyde_embedding(query: str) -> list[float]:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.CHEAP_MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write a 2-sentence passage from a corporate due diligence document "
                    f"that answers: {query}\n"
                    f"Be specific and factual. Return only the passage."
                ),
            }
        ],
        max_tokens=150,
    )
    hypothetical = resp.choices[0].message.content.strip()
    embeddings = await get_embeddings_batch_cached([hypothetical])
    return embeddings[0]


async def _route_query(query: str) -> list[str]:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.CHEAP_MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Classify this query to the most relevant document types: {query}\n"
                    f"Options: financial_statement, legal_contract, market_report, "
                    f"management_presentation, other\n"
                    f'Return ONLY valid JSON: {{"types": ["type1"]}}'
                ),
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=50,
    )
    try:
        data = json.loads(resp.choices[0].message.content)
        types = data.get("types", ["other"])
        return [t for t in types if isinstance(t, str)] or ["other"]
    except (json.JSONDecodeError, KeyError):
        return ["other"]
