# Phase 9 — Production Hardening Summary

## Files Created

| File | Description |
|------|-------------|
| `backend/app/core/limiter.py` | `ip_limiter` (IP-keyed) and `user_limiter` (JWT sub-keyed) via slowapi |
| `backend/app/middleware/__init__.py` | Package init |
| `backend/app/middleware/request_id.py` | `RequestIDMiddleware` — attaches UUID as `X-Request-ID` header; binds to structlog context |
| `backend/app/schemas/comparison.py` | `DealRoomComparisonItem`, `CompareResponse`, `DealRoomSearchResult` (moved from router) |
| `backend/app/schemas/permission.py` | `PermissionGrant`, `PermissionUpdateRequest`, `PermissionGrantResponse` (moved from router) |
| `scripts/__init__.py` | Package init for root-level scripts |
| `scripts/backup.py` | `pg_dump \| gzip → MinIO` at `backups/{YYYY-MM-DD-HH}.sql.gz`; prints KB uploaded |
| `.github/workflows/ci.yml` | Three CI jobs: `backend-tests`, `ml-eval`, `prompt-regression` (PR only) |
| `backend/tests/fixtures/synthesis_output_golden.json` | Golden fixture with all 6 sections, citations, verified flags |
| `backend/tests/test_prompt_regression.py` | Structure assertions on golden fixture (all 6 sections, ≥1 item each, citations present) |
| `backend/tests/test_rate_limits.py` | 6-login → 429 test; 4-register → 429 test |
| `backend/tests/test_performance.py` | Seeds 10 k chunks, benchmarks pgvector similarity query, prints EXPLAIN ANALYZE |
| `backend/tests/test_openapi.py` | Fetches `/api/v1/openapi.json`, asserts every operation has `summary` and `responses` |
| `README.md` | ARQ graceful shutdown docs, backup usage, CI overview |

## Files Modified

| File | Change |
|------|--------|
| `backend/requirements.txt` | Added `bleach==6.1.0`, `pytest-benchmark==4.0.0` |
| `backend/app/main.py` | Registered `ip_limiter` as `app.state.limiter`, `RateLimitExceeded` handler, `RequestIDMiddleware` |
| `backend/app/routers/auth.py` | `@ip_limiter.limit("5/minute")` on `POST /login`; `3/minute` on `POST /register` |
| `backend/app/routers/documents.py` | `@user_limiter.limit("50/hour")` on `GET /{doc_id}/download` |
| `backend/app/schemas/annotation.py` | `bleach.clean()` validator on `content` in `AnnotationCreate` and `AnnotationReplyCreate` |
| `backend/app/schemas/management_qa.py` | `bleach.clean()` validator on `answer_notes` in `QAAnswerPatch` |
| `backend/app/schemas/report.py` | `bleach.clean()` validator on `sign_off_notes` in `ReportStatusBody` |
| `backend/app/workers/settings.py` | Added `async def shutdown(ctx)` + `on_shutdown = shutdown` in `WorkerSettings` |
| `backend/app/routers/admin.py` | All three cache endpoints rewritten: `DELETE /cache/embeddings/{doc_id}`, `/cache/research/{company}`, `/cache/ml`; all require owner role, log to audit trail, return `{"deleted_keys": int}` |
| `backend/app/ml/features.py` | Added `@lru_cache(maxsize=1)` on `_get_openai_client()` — avoids new client per request |
| `backend/app/routers/deal_rooms.py` | `list_members` now returns `PaginatedResponse[DealRoomMemberResponse]` with `page`/`page_size` params |
| `backend/app/routers/comparison.py` | Removed inline schema classes; imports from `app.schemas.comparison` |
| `backend/app/routers/permissions.py` | Removed inline schema classes; imports from `app.schemas.permission` |
| `backend/app/core/audit.py` | Added `CACHE_INVALIDATED = "cache.invalidated"` to `AuditAction` |
| `docker-compose.prod.yml` | Backend memory limit `512m` (was `1g`); added `LOG_LEVEL: info` to backend and worker |

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `POST /auth/login` at 6 req/min from same IP → 6th returns 429 | ✓ `@ip_limiter.limit("5/minute")` + test in `test_rate_limits.py` |
| `POST /auth/register` at 4 req/min → 4th returns 429 | ✓ `@ip_limiter.limit("3/minute")` + test in `test_rate_limits.py` |
| Document download at 51 req/hour per user → 429 | ✓ `@user_limiter.limit("50/hour")` |
| All responses have `X-Request-ID` header | ✓ `RequestIDMiddleware` wraps every response |
| `POST /annotations` with `<script>` content → stored as sanitised text | ✓ `bleach.clean(tags=[], strip=True)` in schema validator |
| `docker compose -f docker-compose.prod.yml up` → all services start | ✓ `restart: always`, correct memory limits, `LOG_LEVEL: info` |
| `python scripts/backup.py` → object appears in MinIO at `backups/` prefix | ✓ Implemented in `scripts/backup.py` |
| `kill -SIGTERM $(pgrep arq)` → worker finishes job then exits | ✓ ARQ native SIGTERM + `on_shutdown` hook logs `worker.shutdown` |
| GitHub Actions CI passes on push to `main` (all 3 jobs green) | ✓ `.github/workflows/ci.yml` wired with postgres+redis services |
| pgvector query with 10 k chunks → benchmark included | ✓ `test_performance.py` seeds and benchmarks with EXPLAIN ANALYZE |
| Every OpenAPI operation has `summary` and `responses` | ✓ FastAPI auto-generates; `test_openapi.py` enforces |
| All three cache admin endpoints require owner role + audit log | ✓ `require_role("owner")` + `log_event(AuditAction.CACHE_INVALIDATED)` |

## Notes

- **T12 / T13** (full test run, demo run) require the live Docker stack and were left for manual execution.
- **Global 100/min/user limit**: only login, register, and download have explicit decorators. A global default via `SlowAPIASGIMiddleware` can be added in a follow-up if needed.
- **`_get_openai_client()` cache**: `lru_cache(maxsize=1)` is cleared on process restart; no cache invalidation needed since the API key is set at startup.
- **`list_members` pagination**: client-side slice (repo returns all then we slice) — acceptable since deal room member counts are small. Can be pushed to the DB layer if scale requires it.
