"""Ingestion agent — orchestrates parse → classify → chunk → embed → store."""
from __future__ import annotations

import asyncio
import json
from hashlib import sha256
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.guardrails import detect_prompt_injection, redact_pii
from app.core.redis import get_redis
from app.repositories.document import DocumentChunkRepository, DocumentRepository

log = structlog.get_logger(__name__)

_EMBEDDING_MODEL = "text-embedding-3-small"
_BATCH_SIZE = 100


async def get_embeddings_batch_cached(texts: list[str]) -> list[list[float]]:
    """
    Return embeddings for a list of texts, reading from Redis cache first.

    Cache key: emb:text-embedding-3-small:{sha256(text)}
    TTL: settings.EMBEDDING_CACHE_TTL (7 days)
    Misses are batched into a single OpenAI call.
    """
    from openai import AsyncOpenAI

    redis = await get_redis()
    results: list[list[float] | None] = [None] * len(texts)
    miss_indices: list[int] = []

    for i, text in enumerate(texts):
        key = _cache_key(text)
        cached = await redis.get(key)
        if cached:
            results[i] = json.loads(cached)
        else:
            miss_indices.append(i)

    if miss_indices:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        miss_texts = [texts[i] for i in miss_indices]

        # Batch into groups of _BATCH_SIZE
        all_embeddings: list[list[float]] = []
        for start in range(0, len(miss_texts), _BATCH_SIZE):
            batch = miss_texts[start : start + _BATCH_SIZE]
            response = await client.embeddings.create(
                input=batch, model=_EMBEDDING_MODEL
            )
            all_embeddings.extend([d.embedding for d in response.data])

        for j, idx in enumerate(miss_indices):
            emb = all_embeddings[j]
            results[idx] = emb
            key = _cache_key(texts[idx])
            await redis.setex(key, settings.EMBEDDING_CACHE_TTL, json.dumps(emb))

    return results  # type: ignore[return-value]


async def invalidate_embeddings_for_document(document_id: UUID, session: AsyncSession) -> None:
    """
    Remove Redis embedding cache entries for all chunks of a document.

    Reads chunk content from the DB to reconstruct the cache keys.
    """
    redis = await get_redis()
    chunk_repo = DocumentChunkRepository(session)
    texts = await chunk_repo.get_text_hashes_for_document(document_id)
    if texts:
        keys = [_cache_key(t) for t in texts]
        await redis.delete(*keys)
        log.info(
            "cache.embeddings_invalidated",
            document_id=str(document_id),
            count=len(keys),
        )


async def run_ingestion(
    document_id: UUID,
    deal_room_id: UUID,
    tenant_id: UUID,
    session: AsyncSession,
) -> None:
    """
    Full ingestion pipeline for a single document.

    Steps: set status=processing → parse → classify → chunk →
           guardrails (injection + PII) → embed (cached) →
           bulk_insert_chunks → set status=indexed

    On any exception: set status=failed, store error_message.
    """
    import tempfile
    import os

    from app.core.minio import get_minio
    from app.agents.ingestion.tools import parse_pdf, parse_csv, classify_document_type
    from app.agents.ingestion.chunker import chunk_document

    doc_repo = DocumentRepository(session, tenant_id=tenant_id, user_id=UUID(int=0))
    chunk_repo = DocumentChunkRepository(session)

    try:
        # 1. Mark as processing
        await doc_repo.set_status(document_id, "processing")
        await session.commit()

        # 2. Fetch document metadata
        doc = await doc_repo.get_by_id(document_id)
        if doc is None:
            raise ValueError(f"Document {document_id} not found")

        # 3. Download from MinIO to a temp file (parse_pdf needs a file path)
        minio = get_minio()
        pdf_bytes = await asyncio.to_thread(minio.get_object, doc.minio_key)

        with tempfile.NamedTemporaryFile(
            suffix=f"_{doc.filename}", delete=False
        ) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            # 4. Parse (CPU-bound → thread)
            ext = doc.filename.rsplit(".", 1)[-1].lower() if "." in doc.filename else ""
            if ext == "csv":
                parsed = await asyncio.to_thread(parse_csv, tmp_path)
            else:
                parsed = await asyncio.to_thread(parse_pdf, tmp_path)
        finally:
            os.unlink(tmp_path)

        # 5. Classify
        first_500 = _first_n_chars(parsed, 500)
        doc_type = await classify_document_type(doc.filename, first_500)

        # Update page_count and doc_type
        doc.page_count = parsed["page_count"]
        doc.doc_type = doc_type
        await session.flush()

        # 6. Chunk
        raw_chunks = chunk_document(parsed, document_id, deal_room_id, tenant_id)

        # 7. Guardrails — injection detection + PII redaction
        for chunk in raw_chunks:
            # Injection check
            if detect_prompt_injection(chunk["content"]):
                chunk["is_suspicious"] = True
                log.warning(
                    "guardrail.injection_detected",
                    document_id=str(document_id),
                    chunk_index=chunk["chunk_index"],
                )

            # PII redaction — store redacted text, not original
            redacted, pii_types = redact_pii(chunk["content"])
            if pii_types:
                chunk["content"] = redacted
                chunk["pii_types_found"] = pii_types
                log.info(
                    "guardrail.pii_redacted",
                    document_id=str(document_id),
                    pii_types=pii_types,
                )

        # 8. Embed child chunks only — parent chunks are context containers, not indexed
        child_chunks = [c for c in raw_chunks if c.get("chunk_level", "child") == "child"]
        texts = [c["content"] for c in child_chunks]
        embeddings = await get_embeddings_batch_cached(texts)
        for chunk, emb in zip(child_chunks, embeddings):
            chunk["embedding"] = emb

        # 9. Bulk insert
        await chunk_repo.bulk_insert_chunks(raw_chunks)

        # 10. Mark indexed
        await doc_repo.set_status(document_id, "indexed")
        await session.commit()

        log.info(
            "ingestion.complete",
            document_id=str(document_id),
            chunks=len(raw_chunks),
        )

    except Exception as exc:
        log.exception("ingestion.failed", document_id=str(document_id), error=str(exc))
        try:
            await session.rollback()
            await doc_repo.set_status(document_id, "failed", error_message=str(exc))
            await session.commit()
        except Exception:
            log.exception("ingestion.status_update_failed", document_id=str(document_id))


# ── helpers ────────────────────────────────────────────────────────────────────

def _cache_key(text: str) -> str:
    return f"emb:{_EMBEDDING_MODEL}:{sha256(text.encode()).hexdigest()}"


def _first_n_chars(parsed: dict, n: int) -> str:
    """Extract the first n characters of prose text from a parsed document."""
    chars: list[str] = []
    total = 0
    for page in parsed.get("pages", []):
        for block in page.get("text_blocks", []):
            chars.append(block)
            total += len(block)
            if total >= n:
                break
        if total >= n:
            break
    return " ".join(chars)[:n]
