# Phase 2 — Document Ingestion Pipeline
## spec.md

### Overview
Users upload documents (PDF, DOCX, XLSX) to a deal room. Files are stored in MinIO — never in PostgreSQL. An ARQ background worker processes each file: it parses the content, classifies the document type, splits it into chunks, generates embeddings with a Redis cache, and stores everything in pgvector. Users can see per-document processing status in real time by polling a job status endpoint. Downloading a document watermarks it with the user's name and timestamp before streaming.

### User Stories
- As an analyst, I upload one or more PDFs to a deal room and get an immediate response — I don't wait for processing.
- As an analyst, I can see each document's status update from "uploaded" to "processing" to "ready" without refreshing the page.
- As an analyst, if a document fails to process I see a clear error message on that document.
- As an analyst, I download a document and the PDF I receive has my name and the date stamped on every page.
- As a viewer, I can view documents but cannot download them unless explicitly granted download permission.
- As a developer, I can verify that embedding API calls are cached in Redis.

### Requirements
- `POST /api/v1/deal-rooms/{id}/documents` — multipart upload (multiple files), streams each to MinIO, creates document row (status=uploaded), enqueues ARQ `task_ingest_document` job, returns document rows with `arq_job_id`
- `GET /api/v1/deal-rooms/{id}/documents` — list all documents with current status (paginated)
- `DELETE /api/v1/deal-rooms/{id}/documents/{doc_id}` — deletes from MinIO, removes document row and all chunks
- `GET /api/v1/deal-rooms/{id}/documents/{doc_id}/download` — checks `can_download` permission, applies watermark, streams PDF, logs `document.downloaded`
- `GET /api/v1/jobs/{job_id}/status` — returns ARQ job status: queued/in_progress/complete/failed
- MinIO key format: `{tenant_id}/{deal_room_id}/{document_id}_{filename}`
- `task_ingest_document`: set status=processing → parse → classify → chunk → embed (Redis cached) → insert chunks → set status=indexed. On any exception: status=failed, store error_message
- Chunking: prose at 512 tokens / 64 overlap. Tables: one atomic chunk per table, serialised as "TABLE: {caption}\nHeaders: ...\nRow: ..."
- Embeddings: `text-embedding-3-small`, batch of 100, cache key `emb:text-embedding-3-small:{sha256(text)}`, TTL 7 days
- Default permissions on upload: all 4 deal_room_roles get `can_view=True`; `owner` and `senior_analyst` get `can_download=True` additionally
- Watermark: user full_name + email + UTC timestamp, diagonal, every page, via pypdf

### Acceptance Criteria
```bash
# Upload a real PDF → file appears in MinIO at correct path
# Poll /jobs/{id}/status → transitions queued → in_progress → complete
# document_chunks table has rows with non-null embedding vectors
# Redis has emb:* keys after ingestion
# Upload same PDF twice → second run has fewer OpenAI API calls (cache hit)
# Download → opened PDF shows watermark text on first page
# User with can_download=False → 403 on download
# Delete document → MinIO object gone, chunks deleted from pgvector
```
