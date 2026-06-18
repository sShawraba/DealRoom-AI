# Phase 7 — Advanced Features
## tasks.md

- [X] **Task 01** — Write `app/routers/comparison.py`: `GET /api/v1/deal-rooms/compare?ids=` — fetch both rooms via DealRoomRepository (404 if either missing/not member), fetch latest approved reports, build comparison response object with risk scores + red_flag_count (count section_type='red_flags' items) + top 3 executive_summary findings
- [X] **Task 02 [needs 01]** — Write `GET /api/v1/deal-rooms/search?q=&status=` in comparison.py — embed query via `get_embeddings_batch_cached([q])`, run pgvector similarity search over `document_chunks` (tenant_id scoped), return top-10 deal rooms with match score
- [X] **Task 03** — Write `app/routers/permissions.py`: `PATCH /api/v1/documents/{doc_id}/permissions` (delete existing + insert new grants, log), `GET /api/v1/documents/{doc_id}/permissions` — both require owner or senior_analyst role in the deal room
- [X] **Task 04 [needs 01,02,03]** — Register comparison and permissions routers in `app/main.py`
- [X] **Task 05 [needs 01,02,03]** — Write `tests/test_advanced.py`: compare two rooms (200 with both risk scores), non-member gets 404, restrict document and verify analyst's RAG excludes it, precedent search returns relevant deals
- [X] **Task 06 [needs 05]** — Run `pytest tests/test_advanced.py -v` — all pass

- [X] **Task 07 (pagination — search)** — Update `GET /api/v1/deal-rooms/search` to return `PaginatedResponse[DealRoomSearchResult]` with `?page=1&page_size=10`. `DealRoomSearchResult` includes id, name, target_company, risk_tier, match_score.
- [X] **Task 08 (DI check)** — Verify `app/routers/comparison.py` and `app/routers/permissions.py` use `Depends()` for session and current_user. No direct construction.
