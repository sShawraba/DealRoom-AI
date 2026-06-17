# Phase 1 — Auth, Tenancy & Access Control
## spec.md

### Overview
Build the complete authentication and access control system. A user registers and a tenant workspace is created simultaneously. Authentication uses JWTs. Access is enforced at three independent layers: tenant (every query scopes to tenant_id), deal room (explicit membership required — non-members get 404 not 403), and document permissions (per-document ACL, wired but not enforced until Phase 2). Every state-changing action writes to an append-only audit log.

### User Stories
- As a new user, I register with my email, password, full name, and firm name — I get a JWT immediately.
- As a registered user, I log in with email and password and receive a JWT.
- As an authenticated user, I can create a deal room and invite team members to it.
- As an admin, I can change a member's role or remove them from a deal room.
- As a user not invited to a deal room, I receive 404 when I try to access it — not 403.
- As a developer, I can see every login, deal room creation, and member invitation in the audit log.
- As a DB admin, I cannot DELETE or UPDATE rows in audit_log — the DB user does not have that permission.

### Requirements

**Auth**
- `POST /api/v1/auth/register` — creates Tenant + User in one transaction, returns JWT
- `POST /api/v1/auth/login` — verifies password, returns JWT
- JWT payload: `{sub: user_id, tenant_id, role, exp}`
- `get_current_user` FastAPI dependency: decodes JWT, returns `CurrentUser(id, tenant_id, role, email, full_name)`
- `require_role(*roles)` dependency factory: raises 403 if current user's tenant-level role not in list

**Tenancy**
- Every data table has `tenant_id UUID NOT NULL`
- `BaseTenantRepository(session, tenant_id, user_id)` base class: `_base_query()` filters by `tenant_id`, full CRUD methods
- `DealRoomRepository` overrides `_base_query()` to also join through `deal_room_members` — if user is not a member, the row is invisible

**Deal Rooms**
- `POST /api/v1/deal-rooms` — creates deal room, auto-adds creator as member with role `owner`
- `GET /api/v1/deal-rooms` — lists only deal rooms the user is a member of
- `GET /api/v1/deal-rooms/{id}` — 404 if not a member
- `PATCH /api/v1/deal-rooms/{id}` — owner or senior_analyst only
- `DELETE /api/v1/deal-rooms/{id}` — owner only

**Membership**
- `POST /api/v1/deal-rooms/{id}/members` — invite by email (owner only); creates deal_room_members row
- `DELETE /api/v1/deal-rooms/{id}/members/{user_id}` — remove member (owner only)
- `PATCH /api/v1/deal-rooms/{id}/members/{user_id}` — change role (owner only)
- `GET /api/v1/deal-rooms/{id}/members` — list members (any member)

**Document Permissions (stub)**
- `document_permissions` table created with columns — no enforcement logic yet (Phase 2 adds that)

**Audit Log**
- `audit_log` table: bigserial PK, append-only
- `log_event(session, actor, action, resource_type, ...)` helper — writes in same transaction as the action
- DB migration includes: `REVOKE DELETE, UPDATE ON audit_log FROM dealroom_app_user`
- Events logged in this phase: `user.login`, `user.login_failed`, `user.registered`, `deal_room.created`, `deal_room.accessed`, `permission.member_invited`, `permission.member_removed`, `permission.role_changed`

**Pagination**
- All list endpoints: `?page=1&page_size=20` query params
- Response shape: `{items: [...], total: int, page: int, page_size: int}`

### Acceptance Criteria
```bash
# Register two firms, verify JWT contains tenant_id
# Create deal rooms for Firm A — Firm B token gets 404 on all Firm A endpoints
# User B not invited to Room 1 — gets 404 on GET /deal-rooms/{room1_id}
# Analyst tries to DELETE deal room — gets 403
# audit_log has rows for register, login, deal_room.created, member_invited
# psql: DELETE FROM audit_log; → ERROR: permission denied
# GET /deal-rooms?page=1&page_size=5 → returns {items, total, page, page_size}
```
