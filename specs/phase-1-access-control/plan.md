# Phase 1 — Auth, Tenancy & Access Control
## plan.md

### New Files
```
backend/app/
  core/
    security.py          hash_password, verify_password, create_access_token, decode_token
    deps.py              get_current_user, require_role, get_db_session
    audit.py             AuditAction constants, log_event() helper
  models/
    tenant.py            Tenant
    user.py              User (role: user_role enum)
    deal_room.py         DealRoom
    deal_room_member.py  DealRoomMember (unique: deal_room_id + user_id)
    document_permission.py  DocumentPermission (stub — columns only)
    audit_log.py         AuditLog (bigserial, no updated_at)
  schemas/
    auth.py              RegisterRequest, LoginRequest, TokenResponse
    deal_room.py         DealRoomCreate, DealRoomResponse, DealRoomMemberResponse
    pagination.py        PaginatedResponse[T] generic
  repositories/
    base.py              BaseTenantRepository[T] with _base_query, get_by_id, list_all, create, update, delete
    deal_room.py         DealRoomRepository (overrides _base_query with membership join)
    audit_log.py         AuditLogRepository (insert only — no list method yet)
  routers/
    auth.py              /register, /login
    deal_rooms.py        CRUD + member management
  middleware/
    tenant.py            (reserved — tenant context injected via JWT dep, not middleware)
```

### Models

```python
# ENUMs (in models/base.py)
user_role      = Enum('admin','analyst','viewer', name='user_role')
deal_room_role = Enum('owner','senior_analyst','analyst','viewer', name='deal_room_role')
deal_status    = Enum('active','archived','closed', name='deal_status')

# models/tenant.py
class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    id   = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)  # lowercased firm name

# models/user.py
class User(Base, TimestampMixin):
    __tablename__ = "users"
    id              = Column(UUID, primary_key=True, default=uuid4)
    tenant_id       = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    email           = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name       = Column(String, nullable=False)
    role            = Column(user_role, default="analyst", nullable=False)
    is_active       = Column(Boolean, default=True)

# models/deal_room.py
class DealRoom(Base, TimestampMixin):
    __tablename__ = "deal_rooms"
    id             = Column(UUID, primary_key=True, default=uuid4)
    tenant_id      = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    created_by     = Column(UUID, ForeignKey("users.id"), nullable=False)
    name           = Column(String, nullable=False)
    target_company = Column(String, nullable=False)
    description    = Column(String)
    status         = Column(deal_status, default="active", nullable=False)
    risk_tier      = Column(String)   # set after ML scoring
    risk_score     = Column(Float)

# models/deal_room_member.py
class DealRoomMember(Base):
    __tablename__ = "deal_room_members"
    id           = Column(UUID, primary_key=True, default=uuid4)
    tenant_id    = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    deal_room_id = Column(UUID, ForeignKey("deal_rooms.id"), nullable=False)
    user_id      = Column(UUID, ForeignKey("users.id"), nullable=False)
    role         = Column(deal_room_role, default="analyst", nullable=False)
    invited_by   = Column(UUID, ForeignKey("users.id"))
    invited_at   = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("deal_room_id", "user_id"),)

# models/audit_log.py
class AuditLog(Base):
    __tablename__ = "audit_log"
    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id     = Column(UUID, nullable=False)
    deal_room_id  = Column(UUID)
    actor_id      = Column(UUID, nullable=False)
    actor_email   = Column(String, nullable=False)
    actor_role    = Column(String, nullable=False)
    action        = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id   = Column(UUID)
    resource_name = Column(String)
    metadata_     = Column("metadata", JSONB, default={})
    ip_address    = Column(INET)
    user_agent    = Column(String)
    occurred_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

### BaseTenantRepository
```python
class BaseTenantRepository(Generic[ModelType]):
    def __init__(self, session: AsyncSession, tenant_id: UUID, user_id: UUID):
        self.session, self.tenant_id, self.user_id = session, tenant_id, user_id

    def _base_query(self):
        return select(self.model).where(self.model.tenant_id == self.tenant_id)

    async def get_by_id(self, id: UUID) -> ModelType | None: ...
    async def list_all(self, page=1, page_size=20, **filters) -> tuple[list, int]: ...
    async def create(self, **kwargs) -> ModelType: ...
    async def update(self, id: UUID, **kwargs) -> ModelType | None: ...
    async def delete(self, id: UUID) -> bool: ...
```

### DealRoomRepository
```python
def _base_query(self):
    return (
        select(DealRoom)
        .join(DealRoomMember, and_(
            DealRoomMember.deal_room_id == DealRoom.id,
            DealRoomMember.user_id      == self.user_id,
            DealRoomMember.tenant_id    == self.tenant_id,
        ))
        .where(DealRoom.tenant_id == self.tenant_id)
    )
```

### AuditAction Constants
```python
class AuditAction:
    USER_LOGIN             = "user.login"
    USER_LOGIN_FAILED      = "user.login_failed"
    USER_REGISTERED        = "user.registered"
    DEAL_ROOM_CREATED      = "deal_room.created"
    DEAL_ROOM_ACCESSED     = "deal_room.accessed"
    MEMBER_INVITED         = "permission.member_invited"
    MEMBER_REMOVED         = "permission.member_removed"
    ROLE_CHANGED           = "permission.role_changed"
    # (more added in later phases)
```

### Migration
- Migration `002_auth_and_access.py` creates: tenants, users, deal_rooms, deal_room_members, document_permissions (stub), audit_log
- Indexes: users(tenant_id), users(email), deal_rooms(tenant_id), deal_room_members(user_id), deal_room_members(deal_room_id), audit_log(tenant_id, deal_room_id), audit_log(occurred_at DESC)
- After table creation: `op.execute("REVOKE DELETE, UPDATE ON audit_log FROM PUBLIC")`
- Trigger: `update_updated_at` function + triggers on tenants, users, deal_rooms

### Register Flow
```python
async def register(body: RegisterRequest, session):
    async with session.begin():
        slug = slugify(body.tenant_name)
        tenant = Tenant(name=body.tenant_name, slug=slug)
        session.add(tenant)
        await session.flush()
        user = User(tenant_id=tenant.id, email=body.email,
                    hashed_password=hash_password(body.password),
                    full_name=body.full_name, role="admin")
        session.add(user)
        await session.flush()
        await log_event(session, user, AuditAction.USER_REGISTERED, "user", user.id, user.email)
    return create_access_token(user.id, tenant.id, user.role, user.email, user.full_name)
```
