# Phase 2 — Document Ingestion Pipeline
## tasks.md

- [X] **Task 01** — Add ENUMs `document_status`, `doc_type` to `app/models/base.py`
- [X] **Task 02 [needs 01]** — Write `app/models/document.py`: `Document` and `DocumentChunk` models with all columns from plan.md. Add `Vector(1536)` import from `pgvector.sqlalchemy`
- [X] **Task 03 [needs 02]** — Create migration `003_documents.py`: documents table + indexes, document_chunks table + HNSW index + composite index
- [X] **Task 04 [needs 02]** — Write `app/repositories/document.py`: `DocumentRepository` (extends BaseTenantRepository), `DocumentChunkRepository` with `bulk_insert_chunks(chunks)` and `delete_by_document_id(doc_id)`
- [X] **Task 05** — Write `app/services/document_service.py`: `upload_to_minio(file, tenant_id, deal_room_id, doc_id)` → returns minio_key; `grant_default_permissions(document_id, deal_room_id, tenant_id, uploader_id, session)` → inserts permission rows for all 4 roles
- [X] **Task 06** — Write `app/agents/ingestion/tools.py`: `parse_pdf(file_path) -> dict` (pdfplumber, returns pages with text_blocks and tables); `classify_document_type(filename, first_500_chars) -> str` (gpt-4o-mini single call)
- [X] **Task 07** — Write `app/agents/ingestion/chunker.py`: `chunk_document(parsed, document_id, deal_room_id, tenant_id) -> list[dict]` — prose via RecursiveCharacterTextSplitter(512, 64), tables as atomic chunks with serialised format
- [X] **Task 08** — Implement `get_embeddings_batch_cached(texts)` in `app/agents/ingestion/agent.py` — SHA-256 cache key, Redis get/set with TTL, batch OpenAI calls for misses only
- [X] **Task 09 [needs 04,05,06,07,08]** — Write `app/agents/ingestion/agent.py`: `run_ingestion(document_id, deal_room_id, tenant_id, session)` — set status=processing, parse, classify, chunk, embed_batch_cached, bulk_insert_chunks, set status=indexed. Catch all exceptions → status=failed, store error_message
- [X] **Task 10 [needs 09]** — Write `app/workers/tasks.py`: `task_ingest_document(ctx, document_id, deal_room_id, tenant_id)` — opens AsyncSessionLocal, calls run_ingestion. Update `workers/settings.py` to include this task in `functions`
- [X] **Task 11** — Write `app/services/document_service.py` watermark function: `stream_watermarked_document(doc, current_user, minio_service) -> bytes` using reportlab to create watermark page + pypdf to merge onto every page
- [X] **Task 12** — Write `app/schemas/document.py`: `DocumentResponse`, `DocumentUploadResponse`, `JobStatusResponse`
- [X] **Task 13 [needs 03,04,05,10,11,12]** — Write `app/routers/documents.py`: POST upload (stream to MinIO, create doc row, enqueue ARQ, grant permissions, log `document.uploaded`), GET list, DELETE (MinIO delete + cascade chunks), GET download (permission check, watermark, stream, log `document.downloaded`)
- [X] **Task 14** — Write `app/routers/jobs.py`: `GET /api/v1/jobs/{job_id}/status` — queries ARQ job status, returns `{job_id, status, error}`
- [X] **Task 15 [needs 13,14]** — Register `documents` and `jobs` routers in `app/main.py`
- [X] **Task 16 [needs 03,09,13]** — Write `tests/test_ingestion.py`: upload real PDF → verify MinIO object exists, verify arq_job_id set, run worker directly (call run_ingestion), verify chunks in DB with non-null embeddings, verify Redis cache keys exist, upload same PDF twice and verify second run has fewer OpenAI calls
- [X] **Task 17 [needs 11,13]** — Write `tests/test_download.py`: download as user with can_download=True → 200 with PDF bytes containing watermark text; download as viewer without download permission → 403
- [X] **Task 18 [needs 16,17]** — Run `pytest tests/test_ingestion.py tests/test_download.py -v` — all pass

- [X] **Task 19 (async fix)** — Wrap `parse_pdf()` call in `run_ingestion()` with `asyncio.to_thread()` — pdfplumber is CPU-bound and blocks the event loop if called directly in async context:
    ```python
    parsed = await asyncio.to_thread(parse_pdf, file_path)
    ```
- [X] **Task 20 (DI fix)** — Update `app/routers/documents.py` to inject `minio: MinioService = Depends(get_minio)` and `arq: ArqRedis = Depends(get_arq_pool)` via `Depends()`. Remove any direct construction of these inside the router.
- [X] **Task 21 (cache invalidation)** — Add `invalidate_embeddings_for_document(document_id: UUID)` to `app/agents/ingestion/agent.py`:
    ```python
    async def invalidate_embeddings_for_document(document_id: UUID):
        redis = await get_redis()
        # chunks for this document were stored with their text hash as key
        # store chunk_text_hashes on document_chunks rows so we can look them up
        # then delete: await redis.delete(*[f"emb:text-embedding-3-small:{h}" for h in hashes])
    ```
    Call this from the document DELETE endpoint before removing chunks from pgvector.
- [X] **Task 22 (schema check)** — Verify `DocumentResponse`, `DocumentUploadResponse`, `JobStatusResponse` are all in `app/schemas/document.py` — not defined in the router file. If any Pydantic model is defined in `routers/documents.py`, move it.

## Guardrails Tasks (apply during ingestion)
- [X] **Task 23 (injection detection)** — In `run_ingestion()`, after chunking and before embedding: call `detect_prompt_injection(chunk.content)`. If True: set `chunk.is_suspicious=True`, log `guardrail.injection_detected` with document_id and chunk_index (not the content). Store the chunk but mark it — synthesis retriever excludes `is_suspicious=True` chunks.
- [X] **Task 24 (PII redaction)** — In `run_ingestion()`, after chunking and before embedding: call `redact_pii(chunk.content)`. Store the redacted text, not the original. Log `guardrail.pii_redacted` with document_id and `pii_types` list (not the values themselves). Update `chunk.pii_types_found`.
