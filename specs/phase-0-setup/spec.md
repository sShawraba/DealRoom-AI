# Phase 0 — Setup & Infrastructure
## spec.md

### Overview
Stand up the full local development stack for DealRoom AI: PostgreSQL with pgvector, Redis, MinIO object storage, a FastAPI backend with an ARQ worker process, and a React frontend — all wired together in Docker Compose. The app must validate its environment at startup, expose health endpoints, emit structured logs, and capture errors in Sentry. No business logic in this phase — foundation only.

### User Stories
- As a developer, I can run `docker compose up --build` and have every service start healthy.
- As a developer, I can hit `/api/v1/health` and get a 200 confirming the app is alive.
- As a developer, I can hit `/api/v1/ready` and see the status of DB, Redis, and MinIO individually.
- As a developer, if a required env var is missing the app refuses to start with a clear error message.
- As a developer, logs in development are human-readable; in production they are JSON.
- As a developer, I can open `http://localhost:9001` and see the MinIO console with a `dealroom-documents` bucket already created.
- As a developer, I can open `http://localhost:5173` and see the React app load.

### Requirements
- Docker Compose runs: `db` (pgvector/pgvector:pg16), `redis` (redis:7-alpine, AOF persistence), `minio`, `minio-init` (creates bucket, exits), `backend`, `worker` (ARQ), `frontend`
- All services have health checks. `backend` and `worker` depend on `db`, `redis`, `minio` being healthy.
- FastAPI app uses lifespan context manager: loads ML model artifact, initialises Redis pool, validates MinIO connectivity on startup.
- `GET /api/v1/health` — always 200, returns `{"status": "ok"}`.
- `GET /api/v1/ready` — checks DB (simple SELECT 1), Redis (PING), MinIO (bucket exists). Returns 200 if all pass, 503 if any fail. Response: `{"db": "ok"|"error", "redis": "ok"|"error", "minio": "ok"|"error"}`.
- All routes prefixed `/api/v1/`.
- CORS: allow `http://localhost:5173` in development, configurable via env in production.
- Startup env validation: `SECRET_KEY`, `DATABASE_URL`, `OPENAI_API_KEY`, `REDIS_URL`, `MINIO_ENDPOINT` are required. App prints missing vars and exits with code 1 if any absent.
- structlog: JSON renderer in production (`APP_ENV=production`), console renderer otherwise.
- Sentry: initialised if `SENTRY_DSN` is set; skipped silently if not.
- React: Vite + React 18 + Tailwind CSS + React Router v6 + Zustand + Axios scaffolded. `npm run dev` serves on port 5173.
- ARQ worker: `Dockerfile.worker` runs `arq app.workers.settings.WorkerSettings`. No tasks defined yet — just the worker process starting cleanly.
- Alembic: initialised. First migration creates the `uuid-ossp` and `vector` extensions only.

### Out of Scope
- Any auth, business models, or agent code.
- Production deployment configuration.
- MinIO TLS or access policy hardening.

### Acceptance Criteria
```bash
docker compose up --build                      # all 7 services healthy, no crash loops
curl localhost:8000/api/v1/health              # {"status":"ok"}
curl localhost:8000/api/v1/ready               # {"db":"ok","redis":"ok","minio":"ok"}
curl localhost:8000/api/v1/docs                # OpenAPI UI loads
docker compose exec redis redis-cli ping       # PONG
docker compose logs backend | grep "startup"   # startup log line visible
open http://localhost:5173                     # React app loads (blank dashboard)
open http://localhost:9001                     # MinIO console, dealroom-documents bucket exists
# Kill a required env var, restart backend — should print missing var and exit 1
```
