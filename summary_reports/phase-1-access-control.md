# Phase 1 — Auth, Tenancy & Access Control: Summary Report

**Completed:** 2026-06-15  
**Tasks:** 20/20 ✓  
**Tests:** 19/19 passed

---

## Files Created / Modified

| File | Purpose |
|------|---------|
| `backend/app/models/base.py` | Base, TimestampMixin, ENUM defs (create_type=False) |
| `backend/app/models/tenant.py` | Tenant ORM model |
| `backend/app/models/user.py` | User ORM model |
| `backend/app/models/deal_room.py` | DealRoom ORM model |
| `backend/app/models/deal_room_member.py` | DealRoomMember with UniqueConstraint |
| `backend/app/models/document_permission.py` | Stub model |
| `backend/app/models/audit_log.py` | Append-only audit log, BigInteger PK |
| `backend/app/models/__init__.py` | Imports all models |
| `backend/migrations/versions/002_auth_and_access.py` | Migration: 7 tables, 4 ENUMs, triggers, immutability trigger |
| `backend/migrations/env.py` | Removed model imports (avoids ENUM double-create conflict) |
| `backend/app/core/security.py` | hash_password, verify_password, create_access_token, decode_token |
| `backend/app/core/audit.py` | AuditAction constants, log_event() |
| `backend/app/core/deps.py` | get_current_user, require_role factory, SessionDep/CurrentUserDep |
| `backend/app/repositories/base.py` | BaseTenantRepository[T] generic base |
| `backend/app/repositories/deal_room.py` | DealRoomRepository with membership-join _base_query |
| `backend/app/repositories/audit_log.py` | INSERT-only AuditLogRepository |
| `backend/app/schemas/auth.py` | RegisterRequest, LoginRequest, TokenResponse |
| `backend/app/schemas/deal_room.py` | DealRoomCreate/Update/Response, member schemas |
| `backend/app/schemas/pagination.py` | PaginatedResponse[T] generic |
| `backend/app/routers/auth.py` | POST /register, POST /login |
| `backend/app/routers/deal_rooms.py` | Full CRUD + member management (8 endpoints) |
| `backend/tests/conftest.py` | Session-scoped app_client, raw asyncpg db_session, clean_db |
| `backend/tests/test_auth.py` | 8 auth tests |
| `backend/tests/test_access_control.py` | 6 access control / tenant isolation tests |
| `backend/tests/test_audit_log.py` | 5 audit log tests |
| `backend/requirements.txt` | Added bcrypt==4.0.1 pin |

---

## Bugs Fixed During Implementation

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Alembic migration fails: `type "user_role" already exists` | `sa.Enum` silently ignores `create_type=False`; only `postgresql.ENUM` honors it | Switched to `PG_ENUM(..., create_type=False)` from `sqlalchemy.dialects.postgresql` |
| Same ENUM double-create via env.py model imports | `import app.models` in `env.py` registers Enum metadata events | Removed model imports from `env.py` (explicit migrations don't need autogenerate) |
| `InvalidRequestError: A transaction is already begun` | Routers called `async with session.begin():` after auto-begin already started on first SELECT | Replaced all `session.begin()` blocks with explicit `await session.commit()` |
| `passlib` fails with `AttributeError: module 'bcrypt' has no attribute '__about__'` | `bcrypt 5.x` removed `__about__`, incompatible with `passlib 1.7.4` | Pinned `bcrypt==4.0.1` in requirements.txt and pip-installed in running container |
| `db_session` audit tests: `asyncpg: cannot perform operation: another operation is in progress` | SQLAlchemy async session (asyncpg) is loop-pinned; session-scoped engine used in function-scoped tests | Replaced `db_session` with raw `asyncpg.Connection` per test |
| `REVOKE DELETE, UPDATE FROM PUBLIC` doesn't block owner | PostgreSQL owner always has all privileges; REVOKE FROM PUBLIC can't remove owner privileges | Added `FOR EACH STATEMENT` trigger `trg_audit_log_immutable` that raises ERRCODE 42501 |
| DELETE/UPDATE trigger doesn't fire for `WHERE id = -1` | Trigger was `FOR EACH ROW` — no rows = no trigger | Changed to `FOR EACH STATEMENT` |

---

## Architecture Notes

- **Three-layer tenant isolation**: `tenant_id` column filter (BaseTenantRepository) → DealRoomMember join (DealRoomRepository) → document_permissions ACL (Phase 3+)
- **Non-member = 404 not 403**: DealRoomRepository._base_query joins members, so non-members get no row, causing 404 — prevents membership inference
- **Append-only audit_log**: immutability enforced by PostgreSQL trigger, not just REVOKE (since owner can't be revoked)
- **JWT payload**: sub (user_id), tenant_id, role, email, full_name — no DB lookup needed per request
- **Session pattern**: FastAPI sessions use auto-begin + explicit `session.commit()` at end of write paths; no `session.begin()` wrappers
