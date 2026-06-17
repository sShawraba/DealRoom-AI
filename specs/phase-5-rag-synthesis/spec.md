# Phase 5 — Advanced RAG, Synthesis & Streaming
## spec.md

### Overview
Build the full Advanced RAG pipeline, Synthesis Agent, and section-level streaming to the frontend. The pipeline has five core stages: query understanding (multi-query + HyDE + routing), parallel retrieval (pgvector HNSW + BM25), RRF fusion, FlashRank cross-encoder re-ranking, and LLM generation with CRAG citation verification. As each of the 6 report sections completes, the worker publishes an event to Redis pub/sub. A FastAPI SSE endpoint streams these events to the browser — sections appear progressively rather than all at once after a 90-second wait.

Contextual compression and CRAG auto-retry are explicitly deferred to post-launch.

### User Stories
- As an analyst, I see the report building in real time — sections appear as they complete rather than everything arriving at once after a long wait.
- As an analyst, I see progress updates: "Researching company → ML scored → Building financial section..."
- As an analyst, 90% or more of factual claims cite a specific source document with filename and page number.
- As the system, if a document is restricted to owner-only, its content never appears in an analyst's report — enforced before the ANN operator runs.
- As an analyst, any uncited claims are flagged with an orange "unverified" badge in the report UI.

### Advanced RAG Pipeline

**Stage 1 — Query Understanding** (per section)
- Multi-query: 3 variant phrasings via gpt-4o-mini
- HyDE: generate a 2-sentence hypothetical document passage, embed it
- Query routing: classify query → doc_type filter
- All three run concurrently via asyncio.gather

**Stage 2 — Parallel Retrieval** (per variant + HyDE embedding)
- pgvector HNSW cosine top-10 per embedding (child chunks, permission-filtered, joins document_permissions BEFORE <=>)
- BM25 keyword top-10 per query variant
- All retrieval calls run concurrently via asyncio.gather

**Stage 3 — RRF Fusion**
- Merge all result sets → deduplicated top-20 per section

**Stage 4 — Cross-Encoder Re-ranking**
- FlashRank re-ranks top-20 → final top-5
- asyncio.to_thread (CPU-bound)

**Stage 5 — Generation + CRAG Verification**
- Per-section LLM call (6 calls total, sections run concurrently where independent)
- System prompt mandates [SOURCE: filename, p.N] on every claim
- Post-generation: parse citations, verify chunk_ids, compute coverage
- Uncited items flagged as is_verified=False — no auto-retry (user resolves via annotations)
- On section complete: publish streaming event to Redis

### Streaming Architecture
- Worker publishes AnalysisEvent to Redis channel `report:{report_id}:events`
- FastAPI SSE endpoint `GET /api/v1/deal-rooms/{id}/reports/{rid}/stream` subscribes and yields events
- Frontend uses EventSource — no polling needed during analysis
- Events: analysis.started, research.started, research.complete, ml.scored, synthesis.started, synthesis.section_complete (×6), analysis.complete, analysis.failed

### Parent-Child Chunking
- Child chunks: 128 tokens — indexed for precise retrieval
- Parent chunks: 512 tokens — served as context to LLM
- On retrieval: search child chunks → fetch parent for context

### Requirements
- `sse-starlette` for FastAPI SSE endpoint
- `flashrank` for local cross-encoder re-ranking
- `rank-bm25` for keyword search
- Sections run as 3 concurrent groups (executive_summary+commercial in parallel, financial_health+red_flags in parallel, legal_flags+key_questions in parallel)
- Full pipeline via ARQ task_run_analysis (already in Phase 3/4 workers)

### Acceptance Criteria
```bash
# Trigger analysis → open browser → sections appear progressively, not all at once
# EventSource connection shows events in browser devtools Network tab
# LangSmith shows multi-query variants + HyDE embedding + re-ranking scores per section
# Citation coverage >= 0.90 logged to structlog
# Restrict a document → re-run → restricted content absent from all sections
# Uncited claim shows orange "unverified" badge in report UI
# analysis.complete event fires → report.status flips to draft in DB
```