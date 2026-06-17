# Phase 1 — Auth, Tenancy & Access Control
## tasks.md

- [ ] **Task 01** — Write `app/models/base.py`: `Base = DeclarativeBase()`, `TimestampMixin` with `created_at`/`updated_at`, all ENUM type definitions (`user_role`, `deal_room_role`, `deal_status`, `risk_tier`)
- [ ] **Task 02 [needs 01]** — Write `app/models/tenant.py`, `app/models/user.py` — Tenant and User ORM models with all columns from plan.md
- [ ] **Task 03 [needs 01]** — Write `app/models/deal_room.py`, `app/models/deal_room_member.py` — DealRoom and DealRoomMember with UniqueConstraint
- [ ] **Task 04 [needs 01]** — Write `app/models/document_permission.py` (stub: columns only, no logic) and `app/models/audit_log.py` (BigInteger PK, no updated_at, metadata_ mapped to "metadata" column)
- [ ] **Task 05 [needs 01,02,03,04]** — Create Alembic migration `002_auth_and_access.py`: all tables, all indexes, REVOKE statement, `update_updated_at` trigger function and triggers on tenants/users/deal_rooms
- [ ] **Task 06** — Write `app/core/security.py`: `hash_password()`, `verify_password()`, `create_access_token(user_id, tenant_id, role, email, full_name)`, `decode_token()` — use `python-jose` HS256
- [ ] **Task 07** — Write `app/core/audit.py`: `AuditAction` class with all constants from plan.md, `log_event(session, actor, action, resource_type, resource_id, resource_name, deal_room_id, metadata, request)` — INSERT only, no commit
- [ ] **Task 08 [needs 06]** — Write `app/core/deps.py`: `get_current_user` dependency (decode JWT → CurrentUser dataclass with id/tenant_id/role/email/full_name), `require_role(*roles)` factory (raises 403), `get_repositories(session, current_user)` helper
- [ ] **Task 09 [needs 01,02,03,04]** — Write `app/repositories/base.py`: `BaseTenantRepository` with `_base_query`, `get_by_id`, `list_all(page, page_size, **filters)` returning `(items, total)`, `create`, `update`, `delete`
- [ ] **Task 10 [needs 09,03]** — Write `app/repositories/deal_room.py`: `DealRoomRepository` overriding `_base_query` with membership join, `get_user_role(deal_room_id, user_id)` returning `deal_room_role | None`
- [ ] **Task 11 [needs 09,04]** — Write `app/repositories/audit_log.py`: INSERT-only — `log(...)` method, no `get_by_id` or `list_all` at this stage
- [ ] **Task 12** — Write `app/schemas/auth.py`: `RegisterRequest`, `LoginRequest`, `TokenResponse`, `CurrentUser` dataclass. Write `app/schemas/deal_room.py`: `DealRoomCreate`, `DealRoomResponse`, `DealRoomMemberResponse`. Write `app/schemas/pagination.py`: `PaginatedResponse[T]` generic Pydantic model
- [ ] **Task 13 [needs 06,07,08,09,10,12]** — Write `app/routers/auth.py`: `POST /api/v1/auth/register` (create tenant + user + audit log in one transaction, return JWT), `POST /api/v1/auth/login` (verify password, log success/failure, return JWT)
- [ ] **Task 14 [needs 08,09,10,11,12]** — Write `app/routers/deal_rooms.py`: GET list (paginated), POST create (auto-add creator as owner member), GET by id (404 if not member), PATCH (senior_analyst+), DELETE (owner only) — all endpoints call `log_event()`
- [ ] **Task 15 [needs 14]** — Add member management to `app/routers/deal_rooms.py`: POST /members (invite by email, owner only), DELETE /members/{user_id} (owner only), PATCH /members/{user_id} (owner only), GET /members (any member)
- [ ] **Task 16 [needs 12,13,14,15]** — Register `auth` and `deal_rooms` routers in `app/main.py`
- [ ] **Task 17 [needs 05,13,14,15]** — Write `tests/test_auth.py`: register, login, invalid password, invalid token, token expiry stub
- [ ] **Task 18 [needs 05,14,15]** — Write `tests/test_access_control.py`: two tenants cannot see each other's deal rooms, non-member gets 404, analyst gets 403 on owner-only endpoint, member invite + remove cycle
- [ ] **Task 19 [needs 05,07]** — Write `tests/test_audit_log.py`: verify audit rows created after register, login, deal_room created, member invited. Verify psql DELETE returns permission denied.
- [ ] **Task 20 [needs 17,18,19]** — Run `pytest tests/test_auth.py tests/test_access_control.py tests/test_audit_log.py -v` — all pass

