<!--
Sync Impact Report
==================
Version change:    N/A (initial fill) → 1.0.0
Previous state:    All placeholders unfilled

Modified principles:
  [PRINCIPLE_1_NAME/DESCRIPTION] → I. Multi-Tenant Security
  [PRINCIPLE_2_NAME/DESCRIPTION] → II. Code Quality
  [PRINCIPLE_3_NAME/DESCRIPTION] → III. Platform Architecture
  [PRINCIPLE_4_NAME/DESCRIPTION] → IV. Product & UX Standards
  [PRINCIPLE_5_NAME/DESCRIPTION] → removed (user supplied 4 principles)

Added sections:
  Technology Stack  (replaces [SECTION_2_NAME/CONTENT])
  CI/CD & Quality Gates  (replaces [SECTION_3_NAME/CONTENT])

Removed sections:
  None

Templates:
  ✅ .specify/memory/constitution.md          — written (this file)
  ✅ .specify/templates/plan-template.md      — Constitution Check gates expanded
  ✅ .specify/templates/spec-template.md      — reviewed, no structural change required
  ✅ .specify/templates/tasks-template.md     — reviewed, no structural change required
  ✅ .specify/templates/checklist-template.md — reviewed, no structural change required

Deferred TODOs:
  None — all fields resolved from user input + today's date.
-->

# DealRoom AI Constitution

## Core Principles

### I. Multi-Tenant Security (NON-NEGOTIABLE)

- Every database table MUST have a `tenant_id` column. Every query MUST filter by
  `tenant_id` — no exceptions, including admin and internal endpoints.
- Deal room access MUST require explicit membership in `deal_room_members`.
- Document access MUST require an explicit grant in `document_permissions`.
- Every state-changing endpoint MUST call `log_event()` before returning a response.
- `audit_log` is INSERT-only. The application database user MUST have no DELETE or
  UPDATE privileges on this table — enforced at the DB role level.
- Long-running tasks (document ingestion, AI analysis) MUST be dispatched through ARQ.
  Use of `FastAPI BackgroundTasks` for these operations is prohibited.
- No secrets or credentials MUST appear in source code. All credentials MUST be loaded
  from vault or `.env` files at application startup.
- File content MUST NOT be stored in PostgreSQL. Binary data MUST reside in MinIO;
  only the object key is stored in the database.
- Every document download MUST be watermarked with the requesting user's name and
  a timestamp before the byte stream is delivered to the client.

**Rationale**: DealRoom AI handles legally sensitive M&A data on behalf of multiple
independent tenants. Cross-tenant data leakage or unauthorized document access is a
critical failure mode that destroys customer trust and creates regulatory liability.

### II. Code Quality (NON-NEGOTIABLE)

- All Python code MUST include type hints on every function and method signature.
  Pydantic MUST be used for all I/O models. Bare `dict` types in function signatures
  are prohibited.
- Every public function and method MUST have a docstring explaining what it does and
  what it returns.
- All database access MUST go through repository classes. Raw queries in router
  handlers are prohibited.
- All routers MUST be thin: validate input → call a service or repository →
  call `log_event()` → return. Business logic does not belong in routers.
- Tests MUST cover: authentication flows, tenant isolation, agent outputs, ML endpoints,
  and the approval gate. Missing coverage in these areas blocks merge.
- CI (test suite + ML eval gate + prompt regression suite) MUST pass before any PR
  is merged to `main`. No exceptions or gate bypasses are permitted.

**Rationale**: AI-generated legal analysis demands high reliability. Type safety,
mandatory repository patterns, and enforced CI gates reduce the risk of silent data
corruption and incorrect analysis reaching customers.

### III. Platform Architecture (NON-NEGOTIABLE)

- All API routes MUST be versioned under `/api/v1/`.
- The service MUST expose `GET /health` (liveness check) and `GET /ready` (readiness
  check verifying DB + Redis connectivity).
- All list endpoints MUST support pagination via `?page=1&page_size=20` and MUST
  include a `total` count in the response envelope.
- Structured JSON logging via `structlog` MUST be used in production. Human-readable
  format is acceptable in development.
- Sentry MUST be configured for error tracking. Every unhandled exception MUST be
  captured with full request context.
- Rate limiting via `slowapi` MUST be applied to all public-facing endpoints.
- Application startup MUST validate all required environment variables and MUST refuse
  to start if any are missing.

**Rationale**: Consistent API contracts, observable infrastructure, and fail-fast
startup prevent silent misconfigurations from reaching production and simplify
SLA monitoring for enterprise customers.

### IV. Product & UX Standards (NON-NEGOTIABLE)

- Every list view MUST render a meaningful empty state — a blank screen is never
  acceptable.
- Every async operation MUST display a loading indicator — a frozen or unresponsive
  UI is never acceptable.
- All user-facing error messages MUST be human-readable and actionable. Raw stack
  traces MUST never be surfaced to end users.
- Approved reports MUST be permanently read-only, enforced at the repository layer —
  not only at the UI or API layers.
- The approval gate MUST be enforced at the API layer. It MUST NOT be bypassable
  from the UI or any API client.
- Report export MUST only be available for reports in `approved` status.

**Rationale**: Due diligence reports are legal artifacts. Immutability after approval
and strict export gating prevent accidental or malicious modification of finalized
analysis, preserving its evidentiary integrity.

## Technology Stack

The following technologies are canonical for DealRoom AI. Deviations require a
constitution amendment with justification.

- **Language**: Python 3.11+
- **API Framework**: FastAPI
- **Task Queue**: ARQ (async Redis Queue) — `FastAPI BackgroundTasks` is prohibited for
  long-running work
- **Object Storage**: MinIO (S3-compatible)
- **Primary Database**: PostgreSQL
- **Cache / Queue Broker**: Redis
- **Logging**: structlog
- **Error Tracking**: Sentry
- **Rate Limiting**: slowapi
- **Data Validation / I/O Models**: Pydantic v2
- **Test Framework**: pytest

## CI/CD & Quality Gates

The following gates MUST all pass on every PR targeting `main`:

1. **Full test suite** (`pytest`) — covering auth, tenant isolation, agent outputs, ML
   endpoints, and the approval gate as a minimum
2. **ML eval gate** — automated evaluation of AI agent output quality against baselines
3. **Prompt regression suite** — detects regressions in LLM prompt behavior
4. **Type checking** (`mypy` or equivalent)
5. **Linting and formatting** (`ruff` or equivalent)

No gate bypass or exception is permitted without a constitution amendment documenting
the justification and a remediation plan.

## Governance

This constitution supersedes all other practice documents, READMEs, and informal team
conventions. When a conflict arises between this document and any other artifact, this
constitution takes precedence.

**Amendment procedure**: Any change to a Core Principle requires a written amendment
proposal, review by at least one peer, and an update to this file with a version bump,
a dated amendment entry, and migration notes for any affected artifacts (templates,
CI configuration, documentation).

**Versioning policy**:
- MAJOR: Removal or backward-incompatible redefinition of a Core Principle.
- MINOR: Addition of a new Principle or Section, or material expansion of guidance.
- PATCH: Clarifications, wording improvements, typo fixes.

**Compliance review**: Every PR review MUST include a Constitution Check — verify that
the implementation does not violate any Core Principle. Violations block merge.

**Runtime guidance**: For feature-level development decisions, consult `plan.md`
(generated per feature by `/speckit-plan`). This constitution defines invariants;
the plan defines strategy.

**Version**: 1.0.0 | **Ratified**: 2026-06-12 | **Last Amended**: 2026-06-12
