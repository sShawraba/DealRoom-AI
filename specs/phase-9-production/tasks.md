# Phase 9 — Production Hardening
## tasks.md

- [ ] **Task 01** — Add `slowapi==0.1.9` and `bleach==6.1.0` to requirements.txt. Add rate limit decorators to: `POST /auth/login` (5/min/IP), `POST /auth/register` (3/min/IP), download endpoint (50/hour/user), all other endpoints (100/min/user via user_limiter)
- [ ] **Task 02** — Write `app/middleware/request_id.py`: `RequestIDMiddleware` from plan.md. Register in `app/main.py`. Verify `X-Request-ID` header present on all responses.
- [ ] **Task 03** — Add input sanitisation using bleach in `app/schemas/annotation.py`, `app/schemas/management_qa.py`, `app/schemas/report.py` (sign_off_notes field) — `field_validator` strips HTML tags
- [ ] **Task 04** — Write `.github/workflows/ci.yml`: three jobs — `backend-tests` (pytest with postgres+redis services, all env vars from secrets), `ml-eval` (python ml/evaluate.py, fails on gate), `prompt-regression` (runs test_prompt_regression.py, only on PR)
- [ ] **Task 05** — Write `tests/test_prompt_regression.py`: load golden fixture, run synthesis on test data, assert all 6 sections present + items have citations + no section is empty
- [ ] **Task 06** — Write `docker-compose.prod.yml`: extend docker-compose.yml with `restart: always`, remove volume bind mounts for source code, add memory limits (backend: 512m, worker: 1g), set `LOG_LEVEL=info`
- [ ] **Task 07** — Write `scripts/backup.py`: pg_dump + gzip + MinIO upload from plan.md. Add `scripts/` dir with `__init__.py`.
- [ ] **Task 08** — Document ARQ graceful shutdown in README. Add `on_shutdown` hook to `WorkerSettings` with a log line.
- [ ] **Task 09** — Write `tests/test_rate_limits.py`: send 6 rapid login requests from same IP → 6th returns 429. Send 51st download request from same user → 429.
- [ ] **Task 10** — Write `tests/test_performance.py` using `pytest-benchmark`: seed deal room with 10,000 document chunks, run pgvector similarity query with permission filter, assert P95 < 200ms. Print EXPLAIN ANALYZE output.
- [ ] **Task 11** — Write `tests/test_openapi.py`: fetch `/api/v1/openapi.json`, iterate all operations, assert each has `summary` and `responses` defined. Fix any missing summaries.
- [ ] **Task 12 [needs 01,02,03,04,05,09,10,11]** — Run full test suite: `pytest tests/ -v --tb=short`. All pass. Push to GitHub → CI pipeline passes (all 3 jobs green).
- [ ] **Task 13** — Final demo run: register → upload 2 real PDFs → trigger analysis → review report → post dispute → resolve → approve → download (check watermark) → send Q&A email → open audit log. No errors. Total time upload-to-report < 120s.

- [ ] **Task 14 (cache admin endpoints)** — Complete `app/routers/admin.py` with all three cache management endpoints:
    - `DELETE /api/v1/admin/cache/embeddings/{document_id}` → calls `invalidate_embeddings_for_document()`
    - `DELETE /api/v1/admin/cache/research/{company_name}` → calls `invalidate_research_cache()`
    - `DELETE /api/v1/admin/cache/ml` → calls `invalidate_ml_cache()`
    All require owner role. All log to audit trail. All return `{"deleted_keys": int}`.
- [ ] **Task 15 (lru_cache audit)** — Grep the entire codebase for functions decorated with `@lru_cache`. Verify at minimum: `get_settings()`, any static FEATURES lists, RISK_TIERS constant builders, SECTION_QUERIES dict builder. Add `@lru_cache` to any pure function called > once per request with the same args.
- [ ] **Task 16 (pagination audit)** — Run `grep -r "async def.*list\|async def get_all\|return \[\]" app/routers/` and verify every list endpoint returns `PaginatedResponse[T]` and not a bare list. Fix any that return unbounded arrays.
- [ ] **Task 17 (DI audit)** — Run `grep -rn "SessionLocal()\|AsyncSessionLocal()\|MinioService()\|AsyncOpenAI()" app/routers/ app/services/`. Any hit that is not inside `app/core/deps.py` or `app/main.py` lifespan is a bug — fix it.
- [ ] **Task 18 (schema audit)** — Run `grep -rn "class.*BaseModel" app/routers/`. Any hit means a Pydantic model is defined in a router file — move it to `app/schemas/`.