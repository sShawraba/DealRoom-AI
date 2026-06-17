"""FlashRank cross-encoder re-ranker wrapper."""
from __future__ import annotations

import asyncio
from functools import lru_cache

import structlog

log = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def get_reranker():
    from flashrank import Ranker
    return Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/app/ml/reranker")


async def rerank(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """Re-rank chunks with FlashRank cross-encoder. Returns top_k sorted by score."""
    if not chunks:
        return chunks

    from flashrank import RerankRequest

    ranker = get_reranker()
    passages = [{"id": str(c["id"]), "text": c["content"]} for c in chunks]
    request = RerankRequest(query=query, passages=passages)

    results = await asyncio.to_thread(ranker.rerank, request)
    score_map = {r["id"]: r["score"] for r in results}

    for chunk in chunks:
        chunk["rerank_score"] = score_map.get(str(chunk["id"]), 0.0)

    ranked = sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)
    log.info("reranker.done", query_preview=query[:60], input=len(chunks), output=top_k)
    return ranked[:top_k]
