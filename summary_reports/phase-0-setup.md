# Phase 0 — Setup & Infrastructure
**Date**: 2026-06-15  
**Status**: COMPLETE

---

## Files Created

| Area | Files |
|---|---|
| **Infra** | `docker-compose.yml` (9 services incl. Vault), `docker-compose.prod.yml`, `.env.example`, `.gitignore` |
| **Backend Dockerfiles** | `backend/Dockerfile`, `backend/Dockerfile.worker` |
| **Backend core** | `config.py` (pydantic-settings, Vault-first), `database.py` (async SQLAlchemy), `redis.py` (async + ARQ pool), `minio.py` (MinioService), `logging.py` (structlog), `vault.py` (hvac + lru_cache), `guardrails.py` (injection/PII/moderation), `deps.py` (central dependency module) |
| **Backend app** | `main.py` (FastAPI factory + lifespan), `routers/health.py` (`/health` + `/ready`), `routers/admin.py` (scaffold), `workers/settings.py` (ARQ) |
| **Alembic** | `alembic.ini`, `migrations/env.py`, `migrations/versions/001_extensions.py` (uuid-ossp + vector) |
| **Models** | `models/base.py`, `models/document_chunk.py` (with guardrail columns) |
| **Frontend** | `Dockerfile`, `package.json`, `vite.config.js`, `tailwind.config.js`, `postcss.config.js`, `index.html`, `src/main.jsx`, `src/App.jsx`, `src/store/authStore.js`, `src/api/client.js` |

---

## Acceptance Criteria

| Check | Result |
|---|---|
| `curl localhost:8000/api/v1/health` | `{"status":"ok"}` |
| `curl localhost:8000/api/v1/ready` | `{"db":"ok","redis":"ok","minio":"ok"}` |
| `curl localhost:8000/api/v1/docs` | HTTP 200 |
| `redis-cli ping` | PONG |
| `http://localhost:5173` | HTTP 200 |
| `http://localhost:9001` | MinIO console (bucket created by minio-init) |
| Vault `startup.complete` log | vault address confirmed in structlog output |
| Worker ARQ | Running, 1 noop function registered |

---

## Bugs Fixed During Smoke Test

1. `SENTRY_DSN=` with inline comment in `.env` was parsed as a non-empty string by pydantic-settings — stripped the comment and added `.strip()` guard in `main.py`.
2. ARQ requires ≥1 registered function — added `_noop` placeholder in `WorkerSettings.functions` (will be replaced in Phase 2).
3. `vault status` healthcheck defaulted to HTTPS while Vault runs on HTTP — switched to `wget` against `/v1/sys/health`.
4. Frontend healthcheck used `curl` which isn't in `node:20-alpine` — switched to `wget`.
