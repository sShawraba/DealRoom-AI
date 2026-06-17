# Phase 0 — Setup & Infrastructure
## tasks.md

- [X] **Task 01** — Create monorepo root: `backend/`, `frontend/`, `ml/`, `specs/`, `docs/`, `.specify/memory/`, `.claude/commands/`
- [X] **Task 02** — Write `docker-compose.yml` with services: db (pgvector/pgvector:pg16), redis (redis:7-alpine --appendonly yes), minio, minio-init, backend, worker, frontend — all with health checks and correct `depends_on`
- [X] **Task 03** — Write `backend/Dockerfile` (python:3.12-slim, install poppler-utils + libpq-dev, copy requirements, create /app/uploads and /app/ml/artifacts)
- [X] **Task 04** — Write `backend/Dockerfile.worker` (same base, CMD: arq app.workers.settings.WorkerSettings)
- [X] **Task 05** — Write `backend/requirements.txt` with all packages from plan.md pinned
- [X] **Task 06 [needs 05]** — Write `backend/app/core/config.py`: pydantic-settings `Settings` class with all env vars, `validate_env()` function that prints missing vars and calls `sys.exit(1)`
- [X] **Task 07 [needs 06]** — Write `backend/app/core/database.py`: async SQLAlchemy engine using `DATABASE_URL`, `AsyncSessionLocal`, `get_session` FastAPI dependency, `Base` declarative base
- [X] **Task 08 [needs 06]** — Write `backend/app/core/redis.py`: `get_redis()` returning async Redis client from `REDIS_URL`, `get_arq_pool()` returning ARQ pool
- [X] **Task 09 [needs 06]** — Write `backend/app/core/minio.py`: `MinioService` with `__init__` (Minio client), `make_key()`, `upload()`, `get_object()`, `delete_object()`, `get_presigned_url()` methods. Singleton `minio_service` instance.
- [X] **Task 10 [needs 06]** — Write `backend/app/core/logging.py`: structlog setup — JSON renderer when `APP_ENV=production`, `ConsoleRenderer` otherwise. `setup_logging()` function called at startup.
- [X] **Task 11 [needs 07,08,09]** — Write `backend/app/routers/health.py`: `GET /api/v1/health` (always 200) and `GET /api/v1/ready` (checks db SELECT 1, redis PING, minio bucket_exists — returns 503 if any fail)
- [X] **Task 12 [needs 06,07,08,09,10,11]** — Write `backend/app/main.py`: FastAPI app factory, lifespan (validate_env, setup_logging, Sentry init if DSN set, ML model load if artifact exists), CORS middleware, register health router, all routes under `/api/v1/`
- [X] **Task 13** — Write `backend/app/workers/settings.py`: `WorkerSettings` with empty `functions = []`, `redis_settings` from `REDIS_URL`, `max_tries=3`, `job_timeout=300`
- [X] **Task 14 [needs 07]** — Initialise Alembic: `alembic init backend/migrations`, configure `env.py` to use `SYNC_DATABASE_URL`, import `Base` from `app.models.base` (create `app/models/__init__.py` and `app/models/base.py` with empty `Base = DeclarativeBase()`)
- [X] **Task 15 [needs 14]** — Create first migration `001_extensions.py`: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` and `CREATE EXTENSION IF NOT EXISTS vector`
- [X] **Task 16** — Write `frontend/package.json` with: react@18, react-dom, react-router-dom@6, axios, zustand, tailwindcss, @vitejs/plugin-react, vite
- [X] **Task 17 [needs 16]** — Write `frontend/vite.config.js`, `tailwind.config.js`, `postcss.config.js`
- [X] **Task 18 [needs 16]** — Write `frontend/src/main.jsx`, `App.jsx` (Router with placeholder routes `/` and `/login`), `store/authStore.js` (Zustand persisted: token, user, setAuth, logout), `api/client.js` (Axios with JWT interceptor and 401 redirect)
- [X] **Task 19** — Write `frontend/Dockerfile` (node:20-alpine, npm install, expose 5173, CMD npm run dev -- --host)
- [X] **Task 20** — Write `.env.example` with all variables from config.py documented with placeholder values and comments
- [X] **Task 21 [needs 02,03,04,12,15,17,18,19]** — Smoke test: `docker compose up --build`, verify all 7 services healthy, curl /health and /ready return expected JSON, MinIO console shows bucket, React app loads at 5173

- [X] **Task 22** — Add `@lru_cache(maxsize=1)` to `get_settings()` in `app/core/config.py`. Add `app/routers/admin.py` scaffold with placeholder cache admin endpoints (implementation in Phase 9). Register admin router in `main.py`.
- [X] **Task 23** — Write `app/core/deps.py`: `get_session()`, `get_redis()`, `get_current_user()` (stub — full implementation in Phase 1), `get_minio()`, `get_arq_pool()`, `get_risk_classifier()` (returns None until Phase 4 loads the model). All future routers import dependencies only from this file.
- [X] **Task 24** — Add global unhandled exception handler to `main.py`: catches all unhandled `Exception`, logs full traceback via structlog, returns `{"detail": "Internal server error"}` with status 500 — stack trace never reaches the client.

## Vault Tasks
- [X] **Task 25** — Add `vault` and `vault-init` services to `docker-compose.yml`. `vault-init` seeds all 8 secret paths listed in plan.md then exits. Add Vault healthcheck to `backend` and `worker` depends_on.
- [X] **Task 26** — Add `hvac==2.1.0` to `requirements.txt`. Write `app/core/vault.py`: `get_vault_client()` with `@lru_cache`, `read_secret(path, key)`, `load_all_secrets()` returning flat dict of all 11 secrets.
- [X] **Task 27 [needs 26]** — Update `app/core/config.py`: move all sensitive fields (database_url, openai_api_key, secret_key, etc.) to empty-default fields. Add `VAULT_ADDR` and `VAULT_TOKEN` as the only vault-related .env fields. Add `VAULT_ROLE_ID` and `VAULT_SECRET_ID` with empty defaults for production AppRole.
- [X] **Task 28 [needs 26,27]** — Update `app/main.py` lifespan: call `load_all_secrets()` first, override settings fields, validate critical secrets non-empty, then proceed with normal startup. If Vault is unreachable the app must fail loudly with a clear error.
- [X] **Task 29 [needs 27]** — Update `.env.example`: only `VAULT_ADDR`, `VAULT_TOKEN`, and non-sensitive config. Remove all API keys and passwords. Add comment explaining Vault populates everything else.
- [X] **Task 30 [needs 25,28,29]** — Smoke test: `docker compose up vault vault-init` → vault-init logs "Vault secrets initialised". `docker compose up backend` → startup log shows "startup.complete" with vault address. `GET /api/v1/ready` returns 200. Confirm no API keys appear anywhere in source code or git history.

## Guardrails Tasks
- [X] **Task 31** — Write `app/core/guardrails.py`: `detect_prompt_injection(text) -> bool`, `redact_pii(text) -> tuple[str, list[str]]`, `moderate_content(text) -> ModerationResult` (async, calls OpenAI moderation API). All three functions exported from this file.
- [X] **Task 32 [needs 31]** — Add `is_suspicious: bool = False` and `pii_types_found: JSON = []` columns to `DocumentChunk` model (migration `001b_chunk_guardrails.py` or include in Phase 2 migration).
