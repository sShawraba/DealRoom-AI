# Phase 9 — Production Hardening
## spec.md

### Overview
Make DealRoom AI deployment-ready. Add rate limiting, a full CI pipeline, production Docker config, database backup, request ID tracking, graceful worker shutdown, and a performance benchmark for pgvector queries.

### Requirements
- **Rate limiting** (slowapi): login 5/min per IP, all other API endpoints 100/min per user, document download 50/hour per user
- **Request ID middleware**: generate UUID per request, attach as `X-Request-ID` response header, include in all structlog log lines
- **GitHub Actions CI** (`.github/workflows/ci.yml`): three jobs — `backend-tests` (pytest with real postgres+redis services), `ml-eval` (`python ml/evaluate.py`, exits 1 on gate fail), `prompt-regression` (golden fixture tests, PR only)
- **docker-compose.prod.yml**: `restart: always` on all services, no volume bind mounts for source code, resource limits (backend: 512m memory, worker: 1g)
- **DB backup script** `scripts/backup.py`: `pg_dump` piped to MinIO as `backups/{YYYY-MM-DD-HH}.sql.gz`, logs backup size, runs clean (no leftover files)
- **Graceful worker shutdown**: ARQ worker catches SIGTERM, finishes current job, then exits cleanly (no mid-job kill)
- **Input sanitisation**: strip HTML tags from all user-generated text fields (annotation content, sign-off notes, Q&A answers) using `bleach.clean()`
- **Performance**: pgvector similarity search on a deal room with 10,000 chunks must complete in < 200ms P95. Add `EXPLAIN ANALYZE` test.
- **OpenAPI completeness**: every endpoint has `summary`, `description`, and `response_model` — verified by a test that fetches `/api/v1/openapi.json` and checks all operations

### Acceptance Criteria
```bash
# POST /auth/login at 6 req/min from same IP → 6th returns 429
# All responses have X-Request-ID header
# GitHub Actions CI passes on push to main (all 3 jobs green)
# docker compose -f docker-compose.prod.yml up → all services start
# python scripts/backup.py → object appears in MinIO at backups/ prefix
# kill -SIGTERM $(pgrep arq) → worker finishes job then exits (check logs)
# POST annotation with <script>alert(1)</script> → stored as sanitised text
# pgvector query with 10k chunks → P95 < 200ms (pytest-benchmark)
```
