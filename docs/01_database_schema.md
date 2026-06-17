# DealRoom AI — Database Schema (v2)

## Setup

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## ENUMs

```sql
CREATE TYPE user_role        AS ENUM ('admin', 'analyst', 'viewer');
CREATE TYPE deal_room_role   AS ENUM ('owner', 'senior_analyst', 'analyst', 'viewer');
CREATE TYPE deal_status      AS ENUM ('active', 'archived', 'closed');
CREATE TYPE document_status  AS ENUM ('uploaded', 'processing', 'indexed', 'failed');
CREATE TYPE report_status    AS ENUM ('draft', 'in_review', 'approved');
CREATE TYPE annotation_type  AS ENUM ('comment', 'verified', 'disputed');
CREATE TYPE risk_tier        AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE section_type     AS ENUM (
  'executive_summary', 'financial_health', 'legal_flags',
  'commercial_assessment', 'red_flags', 'key_questions'
);
CREATE TYPE qa_category AS ENUM ('financial', 'legal', 'operational', 'strategic');
CREATE TYPE qa_priority AS ENUM ('critical', 'high', 'medium');
CREATE TYPE doc_type    AS ENUM (
  'financial_statement', 'legal_contract', 'market_report',
  'management_presentation', 'other'
);
```

---

## Core Tables

### tenants

```sql
CREATE TABLE tenants (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name        TEXT NOT NULL,
  slug        TEXT NOT NULL UNIQUE,
  plan        TEXT NOT NULL DEFAULT 'pro',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### users

```sql
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  email           TEXT NOT NULL UNIQUE,
  hashed_password TEXT NOT NULL,
  full_name       TEXT NOT NULL,
  role            user_role NOT NULL DEFAULT 'analyst',
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email     ON users(email);
```

### deal_rooms

```sql
CREATE TABLE deal_rooms (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  created_by      UUID NOT NULL REFERENCES users(id),
  name            TEXT NOT NULL,
  target_company  TEXT NOT NULL,
  description     TEXT,
  status          deal_status NOT NULL DEFAULT 'active',
  risk_tier       risk_tier,
  risk_score      FLOAT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_deal_rooms_tenant_id ON deal_rooms(tenant_id);
```

---

## Access Control Tables

### deal_room_members

```sql
-- Explicit membership required to access any deal room.
-- A user in the tenant but NOT in this table cannot see the deal room at all.
CREATE TABLE deal_room_members (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  deal_room_id UUID NOT NULL REFERENCES deal_rooms(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role         deal_room_role NOT NULL DEFAULT 'analyst',
  invited_by   UUID REFERENCES users(id),
  invited_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (deal_room_id, user_id)
);

CREATE INDEX idx_deal_room_members_user    ON deal_room_members(user_id);
CREATE INDEX idx_deal_room_members_deal    ON deal_room_members(deal_room_id);
CREATE INDEX idx_deal_room_members_tenant  ON deal_room_members(tenant_id);
```

### document_permissions

```sql
-- Grants access to a specific document within a deal room.
-- Default on upload: all current deal room members inherit view access.
-- Restricted documents require explicit per-user grants.
CREATE TABLE document_permissions (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  -- Either user_id OR role must be set, not both, not neither
  user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
  role         deal_room_role,
  can_view     BOOLEAN NOT NULL DEFAULT TRUE,
  can_download BOOLEAN NOT NULL DEFAULT FALSE,
  granted_by   UUID NOT NULL REFERENCES users(id),
  granted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_user_or_role CHECK (
    (user_id IS NOT NULL AND role IS NULL) OR
    (user_id IS NULL AND role IS NOT NULL)
  )
);

CREATE INDEX idx_doc_perms_document ON document_permissions(document_id);
CREATE INDEX idx_doc_perms_user     ON document_permissions(user_id);
CREATE INDEX idx_doc_perms_tenant   ON document_permissions(tenant_id);
```

---

## Document Tables

### documents

```sql
CREATE TABLE documents (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  deal_room_id    UUID NOT NULL REFERENCES deal_rooms(id) ON DELETE CASCADE,
  uploaded_by     UUID NOT NULL REFERENCES users(id),
  filename        TEXT NOT NULL,
  -- MinIO object key only — no file content in PostgreSQL
  -- Format: {tenant_id}/{deal_room_id}/{document_id}_{filename}
  minio_key       TEXT NOT NULL,
  file_size_bytes BIGINT,
  doc_type        doc_type NOT NULL DEFAULT 'other',
  status          document_status NOT NULL DEFAULT 'uploaded',
  page_count      INT,
  arq_job_id      TEXT,             -- ARQ job ID for status polling
  error_message   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_tenant_deal ON documents(tenant_id, deal_room_id);
CREATE INDEX idx_documents_status      ON documents(status);
```

### document_chunks

```sql
CREATE TABLE document_chunks (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  deal_room_id   UUID NOT NULL REFERENCES deal_rooms(id) ON DELETE CASCADE,
  document_id    UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index    INT NOT NULL,
  content        TEXT NOT NULL,
  content_type   TEXT NOT NULL DEFAULT 'prose',
  page_number    INT,
  section_header TEXT,
  embedding      vector(1536),
  token_count    INT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chunks_embedding   ON document_chunks
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_chunks_tenant_deal ON document_chunks(tenant_id, deal_room_id);
CREATE INDEX idx_chunks_document    ON document_chunks(document_id);
```

---

## Report Tables

### reports

```sql
CREATE TABLE reports (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  deal_room_id        UUID NOT NULL REFERENCES deal_rooms(id) ON DELETE CASCADE,
  created_by          UUID NOT NULL REFERENCES users(id),
  status              report_status NOT NULL DEFAULT 'draft',
  risk_score          FLOAT,
  risk_tier           risk_tier,
  risk_shap_factors   JSONB,
  research_summary    JSONB,
  arq_job_id          TEXT,         -- ARQ job ID for status polling
  total_tokens_used   INT DEFAULT 0,
  estimated_cost_usd  FLOAT DEFAULT 0.0,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_tenant_deal ON reports(tenant_id, deal_room_id);
CREATE INDEX idx_reports_status      ON reports(status);
```

### report_items

```sql
CREATE TABLE report_items (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  deal_room_id   UUID NOT NULL REFERENCES deal_rooms(id) ON DELETE CASCADE,
  report_id      UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  section_type   section_type NOT NULL,
  item_index     INT NOT NULL,
  content        TEXT NOT NULL,
  edited_content TEXT,
  edited_by      UUID REFERENCES users(id),
  edited_at      TIMESTAMPTZ,
  citation       JSONB,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_report_items_report     ON report_items(report_id);
CREATE INDEX idx_report_items_tenant_deal ON report_items(tenant_id, deal_room_id);
```

### report_approvals

```sql
CREATE TABLE report_approvals (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  report_id      UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE UNIQUE,
  approved_by    UUID NOT NULL REFERENCES users(id),
  approved_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sign_off_notes TEXT,
  -- Approval is blocked unless all disputed annotations are resolved.
  -- Enforced in approval_service.py — do not bypass.
  disputed_resolved_count INT NOT NULL DEFAULT 0
);
```

---

## Collaboration Tables

### annotations

```sql
CREATE TABLE annotations (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  deal_room_id   UUID NOT NULL REFERENCES deal_rooms(id) ON DELETE CASCADE,
  report_item_id UUID NOT NULL REFERENCES report_items(id) ON DELETE CASCADE,
  author_id      UUID NOT NULL REFERENCES users(id),
  content        TEXT NOT NULL,
  type           annotation_type NOT NULL DEFAULT 'comment',
  resolved       BOOLEAN NOT NULL DEFAULT FALSE,
  resolved_by    UUID REFERENCES users(id),
  resolved_at    TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_annotations_report_item  ON annotations(report_item_id);
CREATE INDEX idx_annotations_tenant_deal  ON annotations(tenant_id, deal_room_id);
CREATE INDEX idx_annotations_type_resolved ON annotations(type, resolved);
```

### annotation_replies

```sql
CREATE TABLE annotation_replies (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  annotation_id UUID NOT NULL REFERENCES annotations(id) ON DELETE CASCADE,
  author_id     UUID NOT NULL REFERENCES users(id),
  content       TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### management_questions

```sql
CREATE TABLE management_questions (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  deal_room_id   UUID NOT NULL REFERENCES deal_rooms(id) ON DELETE CASCADE,
  report_id      UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  source_item_id UUID REFERENCES report_items(id),
  category       qa_category NOT NULL,
  question       TEXT NOT NULL,
  priority       qa_priority NOT NULL DEFAULT 'medium',
  answered       BOOLEAN NOT NULL DEFAULT FALSE,
  answer_notes   TEXT,
  answered_by    UUID REFERENCES users(id),
  answered_at    TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mgmt_q_report     ON management_questions(report_id);
CREATE INDEX idx_mgmt_q_tenant_deal ON management_questions(tenant_id, deal_room_id);
```

---

## Audit Log Table

```sql
-- Append-only. The application DB user has INSERT only — no UPDATE or DELETE.
-- REVOKE DELETE, UPDATE ON audit_log FROM dealroom_app_user;
-- GRANT INSERT, SELECT ON audit_log TO dealroom_app_user;
CREATE TABLE audit_log (
  id            BIGSERIAL PRIMARY KEY,  -- ordered by insertion time
  tenant_id     UUID NOT NULL,
  deal_room_id  UUID,                   -- null for tenant-level events
  actor_id      UUID NOT NULL,
  actor_email   TEXT NOT NULL,          -- denormalised: survives user deletion
  actor_role    TEXT NOT NULL,          -- role at time of action
  action        TEXT NOT NULL,          -- see AuditAction constants
  resource_type TEXT NOT NULL,
  resource_id   UUID,
  resource_name TEXT,                   -- denormalised for human readability
  metadata      JSONB NOT NULL DEFAULT '{}',
  ip_address    INET,
  user_agent    TEXT,
  occurred_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_tenant_deal  ON audit_log(tenant_id, deal_room_id);
CREATE INDEX idx_audit_occurred_at  ON audit_log(occurred_at DESC);
CREATE INDEX idx_audit_actor        ON audit_log(actor_id);
CREATE INDEX idx_audit_action       ON audit_log(action);
-- Partial index for security-relevant events (fast security queries)
CREATE INDEX idx_audit_security ON audit_log(tenant_id, occurred_at DESC)
  WHERE action IN ('user.login_failed', 'document.downloaded', 'permission.granted', 'permission.revoked');
```

---

## Updated pgvector Retrieval Query (Permission-Filtered)

```sql
-- Every retrieval query must join through document_permissions.
-- This ensures agents never surface content a user is not permitted to see.
-- $1 = query_embedding  $2 = tenant_id  $3 = deal_room_id
-- $4 = user_id          $5 = user_role  $6 = top_k

SELECT
  dc.id,
  dc.content,
  dc.content_type,
  dc.page_number,
  dc.section_header,
  dc.chunk_index,
  d.filename,
  d.doc_type,
  1 - (dc.embedding <=> $1::vector) AS similarity
FROM document_chunks dc
JOIN documents d ON d.id = dc.document_id
JOIN document_permissions dp ON dp.document_id = d.id
WHERE
  dc.tenant_id    = $2::uuid
  AND dc.deal_room_id = $3::uuid
  AND dp.can_view = TRUE
  AND (
    dp.user_id = $4::uuid          -- explicit per-user grant
    OR dp.role = $5::deal_room_role -- role-level grant
  )
ORDER BY dc.embedding <=> $1::vector
LIMIT $6;
```

---

## Default Permission Grant on Document Upload

When a document is uploaded, grant view access to all current deal room members automatically:

```python
# services/document_service.py — after MinIO upload and document row creation

async def grant_default_permissions(
    document_id: UUID,
    deal_room_id: UUID,
    tenant_id: UUID,
    uploader_id: UUID,
    session: AsyncSession
):
    """
    Grant can_view=True to all current deal room members by role.
    Uploader also gets can_download=True.
    Individual restricted documents can have these revoked afterward.
    """
    # Grant view to all roles
    for role in ["owner", "senior_analyst", "analyst", "viewer"]:
        await session.execute(insert(DocumentPermission).values(
            tenant_id=tenant_id,
            document_id=document_id,
            role=role,
            can_view=True,
            can_download=(role in ["owner", "senior_analyst"]),
            granted_by=uploader_id,
        ))
```

---

## updated_at Trigger

```sql
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

-- Apply to: tenants, users, deal_rooms, documents, reports, annotations
```

---

## BaseTenantRepository Pattern (updated)

```python
# repositories/base.py
class BaseTenantRepository(Generic[ModelType]):
    model: Type[ModelType]

    def __init__(self, session: AsyncSession, tenant_id: UUID, user_id: UUID):
        self.session   = session
        self.tenant_id = tenant_id
        self.user_id   = user_id

    def _base_query(self):
        return select(self.model).where(self.model.tenant_id == self.tenant_id)

    # Subclasses that operate on deal-room-scoped models
    # must also filter by deal_room_members membership.
    # See DealRoomRepository for the reference implementation.
```

```python
# repositories/deal_room.py
class DealRoomRepository(BaseTenantRepository[DealRoom]):
    model = DealRoom

    def _base_query(self):
        # Override: require explicit membership
        return (
            select(DealRoom)
            .join(DealRoomMember, and_(
                DealRoomMember.deal_room_id == DealRoom.id,
                DealRoomMember.user_id      == self.user_id,
                DealRoomMember.tenant_id    == self.tenant_id
            ))
            .where(DealRoom.tenant_id == self.tenant_id)
        )
```
