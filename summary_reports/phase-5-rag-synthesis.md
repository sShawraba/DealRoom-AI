# Phase 5 — Advanced RAG, Synthesis & Streaming
**Completed:** 2026-06-15

## Files Created / Modified

| File | Type | Notes |
|------|------|-------|
| `backend/requirements.txt` | Modified | Added `sse-starlette==1.8.2`, `flashrank==0.2.9` |
| `backend/app/services/streaming.py` | Replaced | Full `AnalysisEvent` constants + `publish_progress()` via Redis pub/sub |
| `backend/app/routers/stream.py` | Created | SSE endpoint `GET /api/v1/deal-rooms/{id}/reports/{rid}/stream` |
| `backend/app/models/document.py` | Modified | Added `parent_chunk_id`, `chunk_level` columns to `DocumentChunk` |
| `backend/app/models/report.py` | Created | `Report` + `ReportItem` models with `PgEnum` types |
| `backend/app/models/base.py` | — | No change needed (ENUMs live in report.py) |
| `backend/migrations/versions/004a_parent_child_chunks.py` | Created | Adds parent_chunk_id + chunk_level to document_chunks |
| `backend/migrations/versions/004b_reports.py` | Created | Creates report_status + section_type ENUMs + reports + report_items tables |
| `backend/app/agents/ingestion/chunker.py` | Replaced | Parent (512 tok) + child (128 tok) hierarchy; tables are child-level |
| `backend/app/agents/ingestion/agent.py` | Modified | Only embeds `chunk_level='child'` chunks |
| `backend/app/agents/synthesis/__init__.py` | Created | Package init |
| `backend/app/agents/synthesis/prompts.py` | Created | `SECTION_QUERIES`, `SECTION_GROUPS`, `SYSTEM_PROMPT`, DD checklist |
| `backend/app/agents/synthesis/query_understanding.py` | Created | `understand_query()` — multi-query + HyDE + routing via `asyncio.gather` |
| `backend/app/agents/synthesis/retriever.py` | Created | pgvector HNSW + BM25 + RRF + parent chunk fetch |
| `backend/app/agents/synthesis/reranker.py` | Created | FlashRank wrapper with `lru_cache` + `asyncio.to_thread` |
| `backend/app/agents/synthesis/verifier.py` | Created | CRAG citation parser, coverage %, hallucination detection |
| `backend/app/agents/synthesis/agent.py` | Created | `run_synthesis()` — 3 concurrent groups, per-section streaming events |
| `backend/app/schemas/report.py` | Created | `ReportSummary`, `ReportResponse`, `ReportItemResponse`, `SectionOutput` |
| `backend/app/repositories/report.py` | Created | `ReportRepository` + `ReportItemRepository.bulk_insert_items()` |
| `backend/app/services/report_service.py` | Created | `run_full_analysis_pipeline()` + `generate_missing_context()` |
| `backend/app/workers/tasks.py` | Modified | Added `task_run_analysis()` |
| `backend/app/workers/settings.py` | Modified | Registered `task_run_analysis` in `WorkerSettings.functions` |
| `backend/app/routers/reports.py` | Created | POST/GET list/GET detail for reports |
| `backend/app/main.py` | Modified | Registered `reports_router` + `stream_router` |
| `backend/tests/test_advanced_rag.py` | Created | 9 unit tests + 1 integration test (skipped without fixture) |

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| `test_query_variants_are_different` | ✅ PASS |
| `test_hyde_embedding_correct_dims` | ✅ PASS |
| `test_routing_filters_correctly` | ✅ PASS |
| `test_rrf_no_duplicates` | ✅ PASS |
| `test_reranker_changes_order` | ✅ PASS |
| `test_verifier_flags_hallucination` | ✅ PASS |
| `test_verifier_flags_uncited` | ✅ PASS |
| `test_permission_filter_excludes_restricted` | ✅ PASS |
| `test_streaming_events_published` | ✅ PASS |
| `test_full_pipeline_e2e` | ⏭ Skipped (requires `tests/fixtures/sample_financials.pdf`) |
| DB migrations 004a + 004b | ✅ Applied |
| `sse-starlette` + `flashrank` installed | ✅ In backend + worker containers |

## Architecture

```
POST /api/v1/deal-rooms/{id}/reports
  → enqueues task_run_analysis (ARQ)

task_run_analysis
  → run_full_analysis_pipeline()
      → research agent (cached)                [publishes research.started / research.complete]
      → ML classifier (cached)                 [publishes ml.scored]
      → run_synthesis() ×6 sections            [publishes synthesis.section_complete ×6]
          ↳ understand_query() — 3 concurrent (variants, HyDE, routing)
          ↳ advanced_retrieve() — pgvector+BM25+RRF, permission-filtered
          ↳ rerank() — FlashRank cross-encoder
          ↳ synthesize_section() — GPT-4o with [SOURCE:] citations
      → verify_citations() — CRAG coverage check
      → generate_missing_context()             [publishes analysis.complete]

GET /api/v1/deal-rooms/{id}/reports/{rid}/stream
  → EventSourceResponse subscribing to Redis channel report:{rid}:events
```
