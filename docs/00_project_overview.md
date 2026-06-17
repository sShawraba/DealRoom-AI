# DealRoom AI — Project Overview (v2)

## What We Are Building

DealRoom AI is a multi-tenant SaaS platform where consulting firms conduct AI-powered due diligence on acquisition targets. Each firm gets an isolated workspace. Inside it, every deal gets its own Deal Room — members are explicitly invited, documents are uploaded to MinIO object storage, three AI agents process them, an ML model scores financial risk, and a structured report is generated with citations. The report moves through a governed review workflow (junior → senior analyst) before anything leaves the platform. Every action is logged to an append-only audit trail.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | React 18 (Vite) + Tailwind CSS + React Router v6 |
| Backend | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 + pgvector extension |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Secrets | python-dotenv locally; vault references in prod |
| Task Queue | Redis + ARQ (async-native task queue) |
| Cache | Redis (embedding cache, research cache, ML inference cache) |
| File Storage | MinIO (S3-compatible object storage) |
| Agents | LangGraph + LangChain |
| LLM | OpenAI API — gpt-4o for synthesis, gpt-4o-mini for lightweight calls |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) |
| ML | scikit-learn + XGBoost + SHAP |
| Observability | LangSmith |
| PDF Parsing | pdfplumber |
| Watermarking | pypdf (document download watermarking) |
| Email | SMTP via FastAPI BackgroundTask (aiosmtplib) |
| Containers | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## Monorepo Folder Structure

```
dealroom-ai/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── database.py
│   │   │   ├── redis.py              # Redis client + ARQ pool factory
│   │   │   ├── minio.py              # MinIO client wrapper
│   │   │   └── audit.py              # log_event() helper
│   │   ├── middleware/
│   │   │   └── tenant.py
│   │   ├── models/
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── deal_room.py
│   │   │   ├── deal_room_member.py   # NEW: per-deal membership
│   │   │   ├── document.py
│   │   │   ├── document_permission.py # NEW: per-document ACL
│   │   │   ├── report.py
│   │   │   ├── annotation.py
│   │   │   ├── management_qa.py
│   │   │   └── audit_log.py          # NEW: append-only audit trail
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── tenant.py
│   │   │   ├── deal_room.py
│   │   │   ├── document.py
│   │   │   ├── report.py
│   │   │   ├── annotation.py
│   │   │   ├── management_qa.py
│   │   │   └── audit_log.py          # NEW
│   │   ├── repositories/
│   │   │   ├── base.py
│   │   │   ├── deal_room.py          # UPDATED: membership-gated queries
│   │   │   ├── document.py           # UPDATED: permission-gated queries
│   │   │   ├── report.py
│   │   │   ├── annotation.py
│   │   │   ├── management_qa.py
│   │   │   └── audit_log.py          # NEW: append-only writes only
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── tenants.py
│   │   │   ├── deal_rooms.py         # UPDATED: membership checks
│   │   │   ├── documents.py          # UPDATED: permission checks + watermark
│   │   │   ├── reports.py
│   │   │   ├── annotations.py
│   │   │   ├── management_qa.py
│   │   │   ├── ml.py
│   │   │   ├── permissions.py        # NEW: grant/revoke document permissions
│   │   │   └── audit.py              # NEW: audit log viewer endpoint
│   │   ├── agents/
│   │   │   ├── ingestion/
│   │   │   │   ├── agent.py
│   │   │   │   ├── tools.py
│   │   │   │   └── chunker.py
│   │   │   ├── research/
│   │   │   │   ├── agent.py          # UPDATED: Redis research cache
│   │   │   │   └── tools.py
│   │   │   └── synthesis/
│   │   │       ├── agent.py
│   │   │       ├── retriever.py      # UPDATED: permission-filtered retrieval
│   │   │       └── prompts.py
│   │   ├── ml/
│   │   │   ├── classifier.py         # UPDATED: Redis inference cache
│   │   │   ├── features.py
│   │   │   └── train.py
│   │   ├── services/
│   │   │   ├── document_service.py   # UPDATED: MinIO upload, watermark
│   │   │   ├── report_service.py
│   │   │   ├── approval_service.py
│   │   │   ├── permission_service.py # NEW: assert_can_view/download
│   │   │   └── email_service.py      # NEW: Q&A email dispatch
│   │   └── workers/
│   │       ├── tasks.py              # ARQ task definitions
│   │       └── settings.py           # ARQ WorkerSettings
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_deal_rooms.py
│   │   ├── test_access_control.py    # NEW
│   │   ├── test_audit_log.py         # NEW
│   │   ├── test_agents.py
│   │   └── test_ml.py
│   ├── Dockerfile
│   ├── Dockerfile.worker             # Separate image for ARQ worker
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── DealRoom.jsx
│   │   │   ├── Report.jsx
│   │   │   └── AuditLog.jsx          # NEW: activity log tab
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── deal-rooms/
│   │   │   ├── documents/
│   │   │   ├── report/
│   │   │   ├── annotations/
│   │   │   ├── members/
│   │   │   │   ├── MemberList.jsx    # NEW
│   │   │   │   └── InviteMemberModal.jsx # NEW
│   │   │   └── audit/
│   │   │       └── ActivityFeed.jsx  # NEW
│   │   ├── hooks/
│   │   ├── api/
│   │   └── store/
│   ├── Dockerfile
│   └── package.json
│
├── ml/
├── .github/workflows/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Environment Variables (.env.example)

```env
# App
APP_ENV=development
SECRET_KEY=your-secret-key-here-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database
DATABASE_URL=postgresql+asyncpg://dealroom:password@db:5432/dealroom
SYNC_DATABASE_URL=postgresql://dealroom:password@db:5432/dealroom

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=dealroom-documents
MINIO_SECURE=false

# OpenAI
OPENAI_API_KEY=sk-...

# LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls-...
LANGCHAIN_PROJECT=dealroom-ai

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@yourfirm.com
SMTP_PASSWORD=...
EMAIL_FROM=DealRoom AI <noreply@yourfirm.com>

# ML
ML_MODEL_PATH=/app/ml/artifacts/risk_classifier.pkl

# Cache TTLs (seconds)
EMBEDDING_CACHE_TTL=604800    # 7 days
RESEARCH_CACHE_TTL=86400      # 24 hours
ML_CACHE_TTL=0                # indefinite (0 = no expiry)
```

---

## Architectural Rules (enforce throughout)

1. **Every table has `tenant_id`** — no exceptions for tenant-owned data.
2. **Deal room access requires membership** — every deal room query joins through `deal_room_members`. A user not in the table cannot see the deal room, regardless of tenant.
3. **Document access requires permission** — pgvector retrieval and document downloads join through `document_permissions`. No bypassing for agents.
4. **Audit every state change** — every endpoint that creates, updates, or deletes a resource calls `log_event()` before returning. No exceptions.
5. **Audit log is append-only** — the application DB user has `INSERT` only on `audit_log`. No `UPDATE` or `DELETE` ever.
6. **Long tasks go through ARQ** — document ingestion and full analysis are ARQ tasks, not FastAPI BackgroundTasks. No fire-and-forget threads.
7. **Check Redis cache before every embedding call** — hash the chunk text, check Redis, only call OpenAI on a miss.
8. **Files go to MinIO** — no file content in PostgreSQL. `documents.file_path` stores the MinIO object key only.
9. **Watermark on every download** — apply user name + timestamp watermark before streaming any document to the client.
10. **Approved reports are read-only** — enforced at the repository layer, not just the UI.
