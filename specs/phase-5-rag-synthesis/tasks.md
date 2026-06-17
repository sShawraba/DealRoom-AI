# Phase 5 — Advanced RAG, Synthesis & Streaming
## tasks.md

### Infrastructure
- [ ] **Task 01** — Add `sse-starlette==1.8.2`, `flashrank==0.2.9`, `rank-bm25==0.2.2` to `requirements.txt`
- [ ] **Task 02** — Write `app/services/streaming.py`: `AnalysisEvent` constants, `publish_progress(report_id, event_type, **data)` async function that publishes JSON to Redis channel `report:{report_id}:events`
- [ ] **Task 03 [needs 02]** — Write `app/routers/stream.py`: `GET /api/v1/deal-rooms/{id}/reports/{rid}/stream` using `EventSourceResponse`. Subscribes to Redis pubsub channel, streams events until `analysis.complete` or `analysis.failed`, checks membership (404 if not member). Register in `main.py`.

### Database
- [ ] **Task 04** — Add `parent_chunk_id UUID REFERENCES document_chunks(id)` and `chunk_level TEXT DEFAULT 'parent'` columns to `DocumentChunk` model. Create migration `004a_parent_child_chunks.py`.
- [ ] **Task 05 [needs 04]** — Update Phase 2 chunker: produce parent (512 tokens) and child (128 tokens) chunks per document. Only child chunks get embeddings. Children carry `parent_chunk_id`.
- [ ] **Task 06** — Add `report_status`, `section_type` ENUMs to `app/models/base.py`. Write `app/models/report.py`: `Report` (with `citation_coverage`, `has_unverified` fields) and `ReportItem` (with `is_verified` field). Migration `004b_reports.py`.
- [ ] **Task 07 [needs 06]** — Write `app/repositories/report.py` and `app/schemas/report.py`. Schemas: `ReportSummary`, `ReportItemResponse` (includes `is_verified`), `ReportResponse`, `SectionOutput` Pydantic model for LLM output.

### Stage 1: Query Understanding
- [ ] **Task 08** — Write `app/agents/synthesis/prompts.py`: `SECTION_QUERIES` dict, `SECTION_GROUPS` list of 3 concurrent groups, `SYSTEM_PROMPT` for synthesis LLM call
- [ ] **Task 09 [needs 08]** — Write `app/agents/synthesis/query_understanding.py`: `QueryPlan` dataclass, `understand_query(query)` running `_generate_variants` + `_generate_hyde_embedding` + `_route_query` concurrently via `asyncio.gather()`

### Stage 2–3: Retrieval + RRF
- [ ] **Task 10 [needs 09]** — Write `app/agents/synthesis/retriever.py`: `advanced_retrieve()` with permission-filtered pgvector HNSW (child chunks only, joins `document_permissions` BEFORE `<=>`) + BM25 over same filtered set + `_reciprocal_rank_fusion()` + `_fetch_parent_chunks()`. All concurrent.

### Stage 4: Re-ranking
- [ ] **Task 11** — Write `app/agents/synthesis/reranker.py`: `get_reranker()` with `@lru_cache(maxsize=1)`, `rerank(query, chunks, top_k=5)` via `asyncio.to_thread(ranker.rerank, ...)`. Model downloads to `/app/ml/reranker` on first use.

### Stage 5: Generation + CRAG
- [ ] **Task 12** — Write `app/agents/synthesis/verifier.py`: `verify_citations(sections, retrieved_chunk_ids)` — parses `[SOURCE: filename, p.N]` patterns, checks chunk_ids, computes coverage_pct, marks `is_verified=False` on uncited/hallucinated items
- [ ] **Task 13 [needs 08,09,10,11,12]** — Write `app/agents/synthesis/agent.py`: `synthesize_section()` (single section LLM call with structured JSON output), `run_synthesis()` (runs SECTION_GROUPS concurrently, calls understand→retrieve→rerank→synthesize per section, publishes `SECTION_COMPLETE` event after each, runs CRAG verifier at end)

### Full Pipeline
- [ ] **Task 14 [needs 02,13]** — Write `app/services/report_service.py`: `run_full_analysis_pipeline()` — research → ML → synthesis with streaming events at every stage, persists items, updates report with coverage. `generate_missing_context()` — gpt-4o-mini call comparing found doc_types against DD checklist.
- [ ] **Task 15 [needs 14]** — Add `task_run_analysis(ctx, report_id, deal_room_id, tenant_id, user_id)` to `app/workers/tasks.py`. Add `user_id` parameter (needed for permission-filtered retrieval). Update `WorkerSettings.functions`.
- [ ] **Task 16 [needs 07,15]** — Write `app/routers/reports.py`: `POST /api/v1/deal-rooms/{id}/reports` (validates docs indexed, creates report, enqueues ARQ with user_id, logs `report.analysis_started`). `GET list` (paginated `PaginatedResponse[ReportSummary]`). `GET detail` (full `ReportResponse`). Register in `main.py`.

### Tests
- [ ] **Task 17 [needs 09,10,11,12,13]** — Write `tests/test_advanced_rag.py`:
    - `test_query_variants_are_different`: 3 variants returned, all strings, different from original
    - `test_hyde_embedding_correct_dims`: embedding is list of 1536 floats
    - `test_routing_filters_correctly`: financial query returns financial_statement in filter
    - `test_rrf_no_duplicates`: no duplicate chunk_ids in fused result
    - `test_reranker_changes_order`: at least one position changes after FlashRank
    - `test_verifier_flags_hallucination`: inject non-retrieved chunk_id → flagged as hallucinated
    - `test_permission_filter_excludes_restricted`: restrict doc → not in retrieval results
    - `test_streaming_events_published`: run pipeline, verify Redis channel receives all expected events
    - `test_full_pipeline_e2e`: upload real PDF, run full pipeline directly (bypass ARQ), verify 6 sections + coverage >= 0.90
- [ ] **Task 18 [needs 17]** — Run `pytest tests/test_advanced_rag.py -v` — all pass