# DealRoom AI — Two-Week Work Plan (v2)

## Principles

- Build vertically — a working thin slice beats a wide unfinished feature
- Each day ends with something runnable
- Stub external dependencies early, replace with real implementations later
- Demo target: upload a real PDF, trigger analysis, see a cited report with risk score, annotations, and audit log — in under 90 seconds from upload to report

---

## Week 1 — Foundation + Access Controls + Core Pipeline

---

### Day 1 — Project Scaffold, Auth, and Redis/MinIO Setup

**Goal:** Repo, Docker, JWT auth, Redis, and MinIO all running. You can register and get a token.

- [ ] Monorepo structure (see `00_project_overview.md`)
- [ ] `docker-compose.yml` — postgres (pgvector), redis, minio, backend, worker, frontend
- [ ] `minio-init` service — creates bucket on startup
- [ ] `app/core/config.py` — Settings with all env vars including Redis + MinIO
- [ ] `app/core/database.py` — async SQLAlchemy engine
- [ ] `app/core/redis.py` — async Redis client + ARQ pool factory
- [ ] `app/core/minio.py` — MinioService wrapper (upload, get, delete, presigned URL)
- [ ] `app/core/security.py` — JWT helpers
- [ ] `app/models/` — Tenant, User
- [ ] `alembic init` + first migration (tenants + users)
- [ ] `app/routers/auth.py` — register + login
- [ ] Frontend: Vite + Tailwind + React Router + Zustand auth store + Axios client
- [ ] Frontend: Login.jsx + Register.jsx

**End of day test:** `docker compose up` → register → get JWT → `redis-cli ping` returns PONG → MinIO console shows `dealroom-documents` bucket.

---

### Day 2 — Multi-Tenancy, Deal Rooms, and Membership

**Goal:** Tenant isolation and deal room membership enforced. Two users in the same tenant cannot see deal rooms they are not invited to.

- [ ] `app/models/` — DealRoom, DealRoomMember
- [ ] Migration: deal_rooms + deal_room_members tables
- [ ] `app/repositories/base.py` — BaseTenantRepository with user_id param
- [ ] `app/repositories/deal_room.py` — _base_query joins through deal_room_members
- [ ] `app/routers/deal_rooms.py` — CRUD + membership check on every query
- [ ] `app/routers/deal_rooms.py` — member management endpoints (invite, remove, change role)
- [ ] `app/services/permission_service.py` — assert_can_view, assert_can_download
- [ ] `app/core/audit.py` — AuditAction constants + log_event() helper
- [ ] `app/models/audit_log.py` — AuditLog model (bigserial, append-only)
- [ ] Migration: audit_log table + REVOKE DELETE/UPDATE on audit_log for app user
- [ ] Frontend: Dashboard.jsx — deal room list + risk heatmap cards
- [ ] Frontend: CreateDealRoomModal + InviteMemberModal

**End of day test:** Create two tenants. In Tenant A, create two deal rooms. Invite User B to Room 1 only. Verify User B cannot GET Room 2 (returns 404, not 403). Check audit_log has DEAL_ROOM_CREATED and MEMBER_INVITED entries.

---

### Day 3 — Document Upload, MinIO Storage, and ARQ Ingestion

**Goal:** Upload a PDF, watch it land in MinIO, get chunked and embedded into pgvector via ARQ worker.

- [ ] `app/models/` — Document, DocumentChunk, DocumentPermission
- [ ] Migration: documents + document_chunks (pgvector + HNSW index) + document_permissions tables
- [ ] `app/routers/documents.py` — POST upload (multipart → MinIO) + GET list + DELETE
- [ ] `app/services/document_service.py` — MinIO upload + grant_default_permissions()
- [ ] ARQ: enqueue `task_ingest_document` instead of BackgroundTask
- [ ] `app/workers/tasks.py` — task_ingest_document definition
- [ ] `app/workers/settings.py` — WorkerSettings
- [ ] `app/agents/ingestion/tools.py` — parse_pdf, classify_document_type
- [ ] `app/agents/ingestion/chunker.py` — prose + table chunking
- [ ] `app/agents/ingestion/agent.py` — full pipeline using `get_embeddings_batch_cached()`
- [ ] `GET /api/jobs/{job_id}/status` — ARQ job status polling endpoint
- [ ] Audit log: DOCUMENT_UPLOADED on every upload
- [ ] Frontend: DealRoom.jsx — DocumentUploader + DocumentList + status badges (poll job status)

**End of day test:** Upload a real PDF → ARQ worker picks up job → status goes queued → in_progress → complete → document.status = indexed. Check MinIO console for the file. Query document_chunks — verify rows with embeddings. Check embedding Redis cache populated.

---

### Day 4 — Research Agent + Research Cache

**Goal:** Research agent runs, caches results in Redis, full trace in LangSmith.

- [ ] `app/agents/research/tools.py` — web_search, get_financial_data, get_news_sentiment, get_competitors, get_regulatory_filings
- [ ] `app/agents/research/agent.py` — LangGraph ReAct loop using `run_research_agent_cached()`
- [ ] Redis research cache (see `09_redis.md`)
- [ ] LangSmith tracing with deal_room_id + tenant_id tags
- [ ] Standalone test: `python -m app.agents.research.agent "Acme Corp"` → prints findings + LangSmith trace URL

**End of day test:** Run research agent twice for the same company. First run calls tools (check LangSmith trace). Second run returns from Redis cache (no tool calls in trace). Verify `research:acme_corp:{today}` key exists in Redis.

---

### Day 5 — ML Classifier + Redis Inference Cache

**Goal:** Risk score endpoint works. Results cached in Redis.

- [ ] `ml/train.py` — XGBoost pipeline + 5-fold CV + artifact saved
- [ ] `ml/evaluate.py` — classification report + F1 gate (exits with code 1 on failure)
- [ ] Run training: `python ml/train.py`
- [ ] `app/ml/classifier.py` — RiskClassifier with `predict_cached()` using Redis
- [ ] `app/ml/features.py` — best-effort extraction from document chunks
- [ ] Lifespan: load RiskClassifier at startup + invalidate_ml_cache() on redeploy
- [ ] `app/routers/ml.py` — POST /api/ml/risk-score
- [ ] Audit log: (no audit needed for ML endpoint — read-only)

**End of day test:** POST identical ratios twice → first returns fresh, second returns from cache. Check `ml:risk:*` key in Redis. ML eval gate passes.

---

## Week 2 — Synthesis, Review Workflow, and Polish

---

### Day 6 — Synthesis Agent + Full Analysis Pipeline via ARQ

**Goal:** Full end-to-end pipeline runs via ARQ worker. Report items appear in DB.

- [ ] `app/models/` — Report, ReportItem, ReportApproval
- [ ] Migration: reports + report_items + report_approvals tables
- [ ] `app/agents/synthesis/retriever.py` — hybrid retrieval with permission filtering (see `01_database_schema.md` pgvector query)
- [ ] `app/agents/synthesis/prompts.py` — all prompt templates
- [ ] `app/agents/synthesis/agent.py` — RAG → LLM → SynthesisOutput → persist report_items
- [ ] `app/services/report_service.py` — run_full_analysis_pipeline (research → ML → synthesis)
- [ ] `app/workers/tasks.py` — task_run_analysis
- [ ] `app/routers/reports.py` — POST create (enqueue ARQ job), GET list, GET full report
- [ ] Audit log: REPORT_ANALYSIS_STARTED

**End of day test:** Upload a real annual report → POST /reports → ARQ worker runs full pipeline → GET report → structured sections with citations appear. Check LangSmith for full trace. Verify permission-filtered retrieval (upload a second doc with restricted permissions — confirm its content is not cited in the report).

---

### Day 7 — Report UI + Approval Workflow

**Goal:** Report readable in browser. Senior analyst can approve after resolving disputes.

- [ ] `app/services/approval_service.py` — assert_can_approve (role check + zero disputed check)
- [ ] `app/routers/reports.py` — PATCH item edit + POST approve (role-gated)
- [ ] Audit log: REPORT_ITEM_EDITED, REPORT_SUBMITTED_REVIEW, REPORT_APPROVED
- [ ] Frontend: Report.jsx — three-panel layout
- [ ] Frontend: RiskScoreCard — score + tier + SHAP bars
- [ ] Frontend: ReportSection + ReportItem — render all sections
- [ ] Frontend: ApprovalBar — status-aware (draft / in_review / approved)
- [ ] Frontend: "Submit for Review" (analyst) + "Approve" (senior only, blocked if disputed exist)
- [ ] Frontend: Inline item edit (pencil icon → textarea → PATCH)

**End of day test:** Submit report for review → switch to analyst user → try to approve (blocked, wrong role) → switch to senior analyst → try to approve with an unresolved dispute (blocked, 409 error) → resolve dispute → approve → report locked, export enabled.

---

### Day 8 — Annotations + Document Permissions + Watermarking

**Goal:** Annotations work with threading. Document download watermarks the PDF. Document permissions enforceable.

- [ ] `app/models/` — Annotation, AnnotationReply
- [ ] Migration: annotations + annotation_replies tables
- [ ] `app/routers/annotations.py` — CRUD + resolve + reply
- [ ] `app/routers/documents.py` — GET download with watermark + permission check
- [ ] `app/services/document_service.py` — apply_watermark() using pypdf
- [ ] `app/routers/permissions.py` — PATCH document permissions (restrict/unrestrict)
- [ ] Audit log: ANNOTATION_CREATED, ANNOTATION_DISPUTED, ANNOTATION_RESOLVED, DOCUMENT_DOWNLOADED, DOCUMENT_RESTRICTED
- [ ] Frontend: AnnotationThread + AnnotationBadge
- [ ] Frontend: Annotation polling (15s)
- [ ] Frontend: Type selector (comment / verified / disputed)

**End of day test:** Post a disputed annotation on a report item → see red badge → resolve it → approve report. Download a document → open the PDF → verify watermark shows user name + timestamp + date. Restrict a document to owner only → verify analyst cannot retrieve it from RAG.

---

### Day 9 — Management Q&A, Email, Audit Log UI, and Missing Context

**Goal:** Q&A generates and can be emailed. Activity log visible in UI.

- [ ] `app/models/management_qa.py` — ManagementQuestion
- [ ] Migration: management_questions table
- [ ] `app/routers/management_qa.py` — POST generate + GET + PATCH answer
- [ ] `app/services/email_service.py` — format + send Q&A via aiosmtplib
- [ ] `app/routers/management_qa.py` — POST send-email endpoint
- [ ] Missing context generator — single LLM call in report_service, stored as JSONB on report
- [ ] `app/routers/audit.py` — GET audit log (paginated) + GET export CSV
- [ ] Audit log: QA_GENERATED, QA_EMAIL_SENT, REPORT_EXPORTED
- [ ] Frontend: Q&A panel below report with category groups + priority badges
- [ ] Frontend: "Send Email" button + recipient input modal
- [ ] Frontend: AuditLog.jsx — activity feed with filters + CSV export
- [ ] GitHub Actions CI: backend tests + ml-eval + prompt regression

**End of day test:** Generate Q&A → send email (use Mailtrap or similar SMTP test service) → verify email received with formatted Q&A. Open Audit Log tab — see full chronological activity for the deal room. CI pipeline passes on push.

---

### Day 10 — Deal Comparison, Polish, and Demo Prep

**Goal:** Flawless demo. All features work on two real documents.

- [ ] `app/routers/deal_rooms.py` — GET /compare?deal_room_ids=a,b — returns side-by-side data
- [ ] Frontend: Deal comparison view (two-column report section / risk score comparison)
- [ ] End-to-end run on two real public company annual reports
- [ ] Fix any visual glitches, empty states, error handling gaps
- [ ] Loading skeletons on all async operations (no white screens)
- [ ] README.md with project description + quick start + architecture diagram
- [ ] Demo script written (see below)

---

## Demo Script

1. **Register** a new firm — reach the dashboard in under 30 seconds
2. **Invite a team member** as analyst role — show membership control
3. **Create Deal Room** "Project Falcon — Acme Corp"
4. **Upload 2 PDFs** — watch status go queued → in_progress → ready (via ARQ)
5. **Check Missing Context** — show what documents are still needed from client
6. **Run Analysis** — narrate what the three agents are doing while it runs
7. **Walk the report** — highlight a citation, show the risk score card + SHAP bars
8. **Post a disputed annotation** on a financial finding
9. **Switch to analyst** — try to approve (blocked — show the 409 response)
10. **Resolve the dispute** → approve as senior analyst → report locks
11. **Download a document** — open PDF, show watermark
12. **Generate Q&A** → send email to target (live or Mailtrap)
13. **Open Audit Log** — show full chronological activity with IPs
14. **Compare deals** — show side-by-side risk comparison

---

## Stubs Table

| Feature | Full Implementation | Acceptable Stub |
|---|---|---|
| Web search | Tavily / SerpAPI | Hardcoded JSON for 2-3 known companies |
| News sentiment | NewsAPI + scoring | Return neutral, skip scoring |
| Competitors | Web search + LLM extraction | Hardcoded for demo company |
| SEC EDGAR | EDGAR full-text API | Skip — use web_search fallback |
| Watermark | pypdf per-page stamping | Console.log "watermark applied", skip PDF manipulation |
| Email | aiosmtplib real SMTP | Log email body to console, fake success response |
| BM25 hybrid | rank-bm25 in-memory | Pure pgvector cosine only |
| Redis caches | Full cache + TTL | Uncomment cache.get/set, leave rest working |

---

## Definition of Demo-Ready

- [ ] Register → dashboard in under 30 seconds
- [ ] Upload → indexed in under 90 seconds (via ARQ)
- [ ] Analysis → full report in under 120 seconds
- [ ] Report has at least 3 citations from uploaded PDFs
- [ ] Risk score renders with SHAP factors
- [ ] Disputed annotation blocks approval (409 response visible)
- [ ] Approval locks report (edit buttons hidden)
- [ ] Document download shows watermark in PDF
- [ ] Audit log shows at least 8 distinct event types
- [ ] Two separate tenant accounts cannot see each other's data (test manually)
- [ ] Redis keys visible for embeddings + research cache after a run
- [ ] ARQ worker logs visible in `docker compose logs worker`
