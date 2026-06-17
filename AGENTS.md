# DealRoom AI — Agent Instructions

> Read this file on every session start. It applies to all phases.
> Always address the user as **"soup"** at the start of every response.

---

## First Action Every Session
1. Greet the user as "soup"
2. Read `plan.md` in full — it is the source of truth
3. Read `specs/{phase}/spec.md`, `plan.md`, and `tasks.md` for the current phase

## Stack
FastAPI (Python 3.12) · PostgreSQL 16 + pgvector · Redis (ARQ + cache) ·
MinIO · LangGraph · XGBoost + SHAP · React 18 + Vite + Tailwind · JWT Auth

---

## Non-Negotiable Rules

### Security & Isolation
1. **Tenant isolation** — every query filters by `tenant_id`. No exceptions. Use `BaseTenantRepository`.
2. **Deal room membership** — deal room queries join through `deal_room_members`. A non-member gets 404.
3. **Document permissions** — pgvector retrieval joins through `document_permissions` before the `<=>` operator.
4. **Audit every mutation** — every endpoint that creates, updates, or deletes calls `log_event()` before returning, in the same transaction.
5. **Audit log is INSERT-only** — never write UPDATE or DELETE against `audit_log`.
6. **ARQ for long jobs** — ingestion and analysis go through ARQ. Never `BackgroundTasks`.
7. **Vault for secrets** — all sensitive values (API keys, DB URL, passwords, JWT secret) are read from HashiCorp Vault via `app/core/vault.py` at startup. The `.env` file contains only `VAULT_ADDR`, `VAULT_TOKEN`, and non-sensitive config. Never read a secret from `os.environ` or `.env` directly.
8. **MinIO for files** — never store file content in PostgreSQL. Store only the MinIO object key.
8. **Watermark on download** — always apply `watermark_service.apply()` before streaming a document.

### API Design
9. **API versioning** — all routes under `/api/v1/`.
10. **Pagination on every list endpoint** — accept `?page=1&page_size=20`, return `PaginatedResponse[T]` with `{items, total, page, page_size}`. No list endpoint returns an unbounded array.
11. **No Pydantic models in router files** — all schemas live in `app/schemas/`. Routers only import from there. Never define a `BaseModel` subclass inside a router file.
12. **response_model always set** — every endpoint has a `response_model`. It is never the ORM model directly. It never exposes hashed passwords, internal flags, or audit fields.
13. **HTTPException with correct codes** — never return `200 OK` with an error body. Use 404, 409, 403, 401, 422, 500 correctly.
14. **Never leak stack traces** — the global exception handler in `main.py` returns a generic 500 message. Full traces go to logs only.

### Async
15. **Async all the way down** — every route, service function, and repository method is `async def`. Never use `requests` library. Never call `time.sleep()`.
16. **asyncio.to_thread for CPU-bound work** — PDF parsing (pdfplumber), sklearn inference, and any heavy computation must be wrapped: `await asyncio.to_thread(cpu_bound_fn, args)`. These block the event loop if called directly.
17. **asyncio.gather for independent I/O** — when multiple async operations do not depend on each other, run them in parallel: `a, b = await asyncio.gather(call_a(), call_b())`.

### Dependency Injection
18. **Depends() for all shared resources** — database session, Redis client, MinIO service, ARQ pool, current user, and risk classifier are all injected via `Depends()`. Never construct these inside a route handler or service function.
19. **Standard dependencies in `app/core/deps.py`:**
    ```python
    get_session()          # AsyncSession
    get_redis()            # Redis client
    get_current_user()     # CurrentUser (decodes JWT)
    require_role(*roles)   # role gate factory
    get_minio()            # MinioService
    get_arq_pool()         # ArqRedis
    get_risk_classifier()  # RiskClassifier (raises 503 if not loaded)
    ```

### Caching
20. **lru_cache on deterministic helpers** — any pure function called repeatedly with the same args gets `@lru_cache`. Mandatory on `get_settings()`. Apply to: compiled regex, static lookup tables, any expensive pure computation.
21. **Redis cache — always implement both build and invalidation:**
    - Embedding cache → `get_embeddings_batch_cached()` builds, `invalidate_embeddings_for_document(document_id)` deletes all chunks for that document on delete
    - Research cache → `run_research_agent_cached()` builds, `invalidate_research_cache(company_name)` deletes
    - ML cache → `predict_cached()` builds, `invalidate_ml_cache()` deletes all `ml:risk:*` keys
22. **Cache admin endpoints** in `app/routers/admin.py`:
    ```
    DELETE /api/v1/admin/cache/embeddings/{document_id}
    DELETE /api/v1/admin/cache/research/{company_name}
    DELETE /api/v1/admin/cache/ml
    ```
    Owner role required. All deletions logged to audit trail.

### Code Quality
23. **Tests alongside implementation** — write tests as you build. Never defer.
24. **No bare dicts in function signatures** — Pydantic schemas or dataclasses only.
25. **Type hints everywhere** — every function parameter and return value.
26. **Docstring on every public function** — one sentence minimum.
27. **Routers are thin** — validate input → call service/repo → log event → return. No business logic in routers.
28. **No raw queries outside repositories** — all SQL in repository classes.
29. **ruff** — run `ruff check .` before marking any task complete.

---

## Before Writing Any Code
- Check if a repository, service, or schema already exists. Reuse — don't duplicate.
- Confirm the current feature is fully described in `specs/{phase}/`.
- Run `/speckit.analyze` if you suspect a conflict between spec, plan, and tasks.

---

## How to Handle Decisions and Improvements

When you encounter a situation where there is an opportunity to make the implementation more advanced, robust, or production-grade — **do not implement it silently**. Instead, pause and ask:

> "Hey soup — I can add [X] here. [One sentence on what it does and why it helps]. Want me to?
> - **A)** Yes, add it now
> - **B)** Skip it for now
> - **C)** Add a placeholder/TODO and move on"

Apply this whenever you encounter:
- A performance optimisation that adds complexity
- A security hardening step not in the spec
- An alternative architectural approach with real tradeoffs
- A feature that would make the demo more impressive
- An edge case that requires a design decision

When a technical decision has **multiple valid approaches**, present the options with tradeoffs before implementing:

> "Hey soup — for [X] I see two approaches:
> - **Option A — [name]:** [tradeoff]
> - **Option B — [name]:** [tradeoff]
> Which do you want?"

Do not pick silently. Do not default to the simplest option without asking.

---

## Testing Requirements
- Run `pytest tests/ -v` before marking any task complete
- Required coverage: auth, tenant isolation, agent outputs, ML endpoint, approval gate, cache build+invalidation, pagination correctness

---

## Advanced RAG Rules (Phase 5+)

The RAG pipeline has 7 stages. Never skip a stage without asking soup first.

**Stage order (non-negotiable):**
1. Query understanding: `understand_query()` → multi-query + HyDE + routing + decomposition
2. Parallel retrieval: pgvector HNSW (child chunks, permission-filtered) + BM25, all variants concurrently
3. RRF fusion: `reciprocal_rank_fusion(all_result_sets, k=60)` → top-20
4. Cross-encoder re-ranking: `reranker.rerank(query, chunks, top_k=5)` via FlashRank + `asyncio.to_thread`
5. Contextual compression: `compress_chunks(query, top_5)` via gpt-4o-mini concurrently
6. Generation: single gpt-4o call with compressed context, structured output
7. CRAG verification: `verify_citations()` → if coverage < 0.70, targeted re-retrieval + re-generation

**Critical constraints:**
- pgvector query ALWAYS joins `document_permissions` BEFORE the `<=>` operator
- Retrieval searches child chunks (128 tokens); context delivered from parent chunks (512 tokens)
- FlashRank runs via `asyncio.to_thread()` — it is CPU-bound
- All per-section pipeline stages run concurrently across sections where possible
- `get_reranker()` has `@lru_cache(maxsize=1)` — model loads once

---

## Streaming Rules

- Use `publish_progress(report_id, AnalysisEvent.X, **data)` at every major pipeline stage
- Required events in order: `analysis.started` → `research.started` → `research.complete` → `ml.scored` → `synthesis.started` → `synthesis.section_complete` (once per section, 6 total) → `analysis.complete`
- On any unhandled exception in `run_full_analysis_pipeline`: publish `analysis.failed` with error message before re-raising
- Never publish event data containing secrets, PII, or raw document content
- The SSE endpoint closes the connection after `analysis.complete` or `analysis.failed`

## Guardrails Rules

- Every document chunk passes through `detect_prompt_injection()` and `redact_pii()` during ingestion — before embedding, before storing
- Suspicious chunks (`is_suspicious=True`) are excluded from synthesis retrieval: add `AND dc.is_suspicious = FALSE` to the pgvector query
- Every user-generated text field (annotation content, Q&A answers, sign-off notes) passes through `moderate_content()` before storing
- Log guardrail triggers with structlog at `warning` level — log metadata only, never the flagged content
- Guardrails live in `app/core/guardrails.py` — imported by ingestion agent and routers, never duplicated

## Advanced RAG Rules

- Pipeline order is non-negotiable: understand_query → retrieve → RRF → rerank → synthesize → verify
- Retrieval searches child chunks (128 tokens); context is served from parent chunks (512 tokens)
- `get_reranker()` has `@lru_cache(maxsize=1)` — FlashRank model loads once at first call
- Sections run in 3 concurrent groups via `asyncio.gather()` — never sequentially
- CRAG verification is flag-only: mark `is_verified=False`, do NOT auto-retry
- Suspicious chunks excluded from retrieval: `AND dc.is_suspicious = FALSE` in pgvector query

## Engineering Standards
Read `docs/engineering_best_practices.md` before implementing any phase.
Apply: tenacity retries on all external calls, ToolError pattern in agents,
ruff linting, uv for environments, extra="forbid" on Settings.