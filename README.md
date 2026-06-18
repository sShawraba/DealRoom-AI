# DealRoom AI

AI-powered M&A due-diligence platform.

## Quick start

```bash
docker compose up
```

The backend API is available at http://localhost:8000/api/v1/docs.

## Production deployment

```bash
docker compose -f docker-compose.prod.yml up -d
```

Resource limits: backend 512 MB, worker 1 GB. All services use `restart: always`.

## ARQ worker — graceful shutdown

The ARQ worker handles `SIGTERM` natively: it finishes the job that is currently
running before exiting. No mid-job kills occur.

To verify clean drain in container logs:

```bash
kill -SIGTERM $(pgrep arq)
# Wait for the current job to complete, then check logs:
docker compose logs worker | grep worker.shutdown
```

Expected log line on clean exit:

```
worker.shutdown  message="Draining and exiting cleanly"
```

The `on_shutdown` hook in `WorkerSettings` (`backend/app/workers/settings.py`)
emits this line so that operators can confirm the drain before the process exits.

## Database backup

```bash
DATABASE_URL=postgresql://... python scripts/backup.py
```

Compresses a `pg_dump` with gzip and uploads to MinIO under `backups/{YYYY-MM-DD-HH}.sql.gz`.

## Running tests

```bash
cd backend
pytest tests/ -v --tb=short
```

CI runs three jobs on every push to `main` and on pull requests:
- **backend-tests** — full pytest suite against real Postgres + Redis
- **ml-eval** — `python ml/evaluate.py` gates on macro F1 ≥ 0.65
- **prompt-regression** — structure checks on the synthesis golden fixture (PR only)
