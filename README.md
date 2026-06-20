# DealRoom AI

AI-powered M&A due diligence platform. Upload financial, legal, and commercial documents into a deal room and get a structured analysis report with risk scoring, source-cited findings, and collaborative annotation — in hours, not weeks.

---

## Screenshots

### Landing Page
![Landing page](<Frontend screenshots/landing_page.png>)

### Dashboard
![Dashboard — deal portfolio with risk distribution](<Frontend screenshots/admin_page.png>)

### Deal Room
![Deal room — document management and team members](<Frontend screenshots/Deal_room.png>)

### Analysis Report
![Analysis report — risk score, findings, and inline annotations](<Frontend screenshots/Analysis_report.png>)

> **Disclaimer:** All company names, documents, financial figures, and analysis data shown in the screenshots are fictional and generated solely for demonstration purposes. Any resemblance to real companies or actual financial data is coincidental.

---

## Features

- **Deal Rooms** — Isolated workspaces per target company. Upload PDFs, XLSXs, and CSVs; documents are chunked, embedded, and indexed automatically.
- **AI Analysis** — Runs a multi-section due diligence report (Executive Summary, Financial Health, Commercial Assessment, Legal Flags, Red Flags, Key Questions) grounded in the uploaded documents with source citations.
- **Risk Scoring** — ML classifier assigns a 0–100 risk score (Low / Medium / High / Critical) per deal room, with a portfolio-level distribution on the dashboard.
- **Annotations** — Analysts can comment on, verify, or dispute individual report findings inline. Disputes are tracked and resolved in the same view.
- **Deal Comparison** — Side-by-side comparison across multiple deal rooms.
- **Management Q&A** — Ask free-form questions against the indexed documents in a deal room; answers are streamed with citations.
- **Permissions** — Role-based access (Owner, Analyst, Viewer) per deal room with invite-by-email flow.
- **Audit Log** — Full tamper-evident event trail (logins, uploads, report runs, permission changes) filterable by user, action, and date range. Admin only.
- **CSV Export** — Export the audit log or analysis reports to CSV.

---

## Quick start

```bash
cp .env.example .env        # fill in OPENAI_API_KEY and any other values
docker compose up
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API + docs | http://localhost:8000/api/v1/docs |
| MailHog (email preview) | http://localhost:8025 |
| MinIO console | http://localhost:9001 |
| Vault UI | http://localhost:8200 |

On first run, `vault-init` seeds all secrets (DB URL, Redis URL, JWT secret key, API keys) into Vault automatically. The backend reads them at startup.

---

## Production deployment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The prod override adds `restart: always` on all services, removes source bind-mounts from the backend and worker (so containers run the built image, not local code), and applies memory limits:

| Service | Memory limit |
|---|---|
| db | 2 GB |
| worker | 1 GB |
| minio | 1 GB |
| backend | 512 MB |
| redis | 512 MB |
| frontend | 256 MB |
| vault | 256 MB |
| mailhog | 64 MB |

---

## Environment variables

Copy `.env.example` to `.env`. Most secrets are stored in Vault and seeded automatically — the only things you need to set manually are:

- `OPENAI_API_KEY` — required for analysis and embeddings
- `LANGCHAIN_API_KEY` — optional, for LangSmith tracing
- `SENTRY_DSN` — optional, for error tracking

See `.env.example` for the full list with descriptions.

---

## Running tests

```bash
cd backend
pytest tests/ -v --tb=short
```

CI runs on every push to `main` and on pull requests:

- **backend-tests** — full pytest suite against real Postgres + Redis
- **ml-eval** — `python ml/evaluate.py` gates on macro F1 ≥ 0.65
- **prompt-regression** — structure checks on the synthesis golden fixture (PR only)

---

## Database backup

```bash
DATABASE_URL=postgresql://... python scripts/backup.py
```

Compresses a `pg_dump` with gzip and uploads to MinIO under `backups/{YYYY-MM-DD-HH}.sql.gz`.

---

## ARQ worker — graceful shutdown

The background worker handles `SIGTERM` natively: it finishes the currently running job before exiting.

```bash
kill -SIGTERM $(pgrep arq)
docker compose logs worker | grep worker.shutdown
```

Expected log line on clean exit:

```
worker.shutdown  message="Draining and exiting cleanly"
```
