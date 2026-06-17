# DealRoom AI — Access Control & Audit Trail

## Overview

DealRoom AI implements VDR-grade access controls with three layers of isolation: tenant isolation (row-level scoping), deal room membership (explicit invitation required), and document-level permissions (granular per-document ACL). Every state-changing action is written to an append-only audit log.

---

## Layer 1 — Tenant Isolation

All tables carry `tenant_id`. The application DB user has row-level access scoped by this column via every query in the `BaseTenantRepository`. This layer is always active and cannot be bypassed from within normal application code.

---

## Layer 2 — Deal Room Membership

Being in a tenant does not grant access to any deal room. Every deal room query joins through `deal_room_members`. A user not explicitly in that table gets a 404 — not a 403 — so they cannot infer whether the deal room exists.

### Roles

| Role | Can view report | Can edit items | Can approve | Can manage members | Can grant doc permissions |
|---|---|---|---|---|---|
| `owner` | Yes | Yes | Yes | Yes | Yes |
| `senior_analyst` | Yes | Yes | Yes | No | Yes |
| `analyst` | Yes | Yes | No | No | No |
| `viewer` | Yes | No | No | No | No |

**Approval rule enforced in `approval_service.py`:**
- Caller must have role `owner` or `senior_analyst` in the deal room
- Zero unresolved `disputed` annotations must exist on the report
- Both conditions checked atomically before status transition

```python
# services/approval_service.py

async def assert_can_approve(report_id: UUID, current_user: CurrentUser, session: AsyncSession):
    # 1. Check caller's deal room role
    member = await get_membership(current_user.id, report.deal_room_id, session)
    if member.role not in ("owner", "senior_analyst"):
        raise HTTPException(403, "Only senior analysts and owners can approve reports")

    # 2. Count unresolved disputed annotations on this report
    disputed_count = await session.scalar(
        select(func.count(Annotation.id))
        .join(ReportItem, ReportItem.id == Annotation.report_item_id)
        .where(
            ReportItem.report_id == report_id,
            Annotation.type == "disputed",
            Annotation.resolved == False
        )
    )
    if disputed_count > 0:
        raise HTTPException(
            409,
            f"Cannot approve: {disputed_count} disputed annotation(s) must be resolved first"
        )
```

### Member Management Endpoints

```
POST /api/deal-rooms/{id}/members
  Auth: owner only
  Body: { email: str, role: deal_room_role }
  - Looks up user by email within the tenant
  - Inserts into deal_room_members
  - Logs: permission.member_invited
  - On new member: grants default document view permissions for all existing docs

DELETE /api/deal-rooms/{id}/members/{user_id}
  Auth: owner only
  - Removes from deal_room_members
  - Revokes all document_permissions for that user in this deal room
  - Logs: permission.member_removed

PATCH /api/deal-rooms/{id}/members/{user_id}
  Auth: owner only
  Body: { role: deal_room_role }
  - Updates role
  - Logs: permission.role_changed

GET /api/deal-rooms/{id}/members
  Auth: any member
  Response: List[{ user_id, full_name, email, role, invited_at }]
```

---

## Layer 3 — Document Permissions

Every document has an ACL in `document_permissions`. Permissions can be role-based (applies to everyone with that role in the deal room) or user-specific (applies to one person).

### Default on upload

All four deal room roles get `can_view = TRUE`. `owner` and `senior_analyst` additionally get `can_download = TRUE`. Analysts and viewers must be explicitly granted download access.

### Restricting a document

An owner or senior analyst can restrict a document after upload — revoking the default role grants and creating explicit per-user grants instead:

```
PATCH /api/documents/{document_id}/permissions
  Auth: owner or senior_analyst of the deal room
  Body: {
    "mode": "restricted",
    "grants": [
      { "user_id": "uuid", "can_view": true, "can_download": true },
      { "role": "senior_analyst", "can_view": true, "can_download": true }
    ]
  }
  - Deletes existing permission rows for this document
  - Inserts new grants from the body
  - Re-indexes: removes existing chunks from vector store, re-embeds with new permission tags
  - Logs: permission.document_restricted

GET /api/documents/{document_id}/permissions
  Auth: owner or senior_analyst
  Response: List[{ user_id | role, can_view, can_download, granted_by, granted_at }]
```

### Permission Service

```python
# services/permission_service.py

async def assert_can_view(user_id: UUID, user_role: str, document_id: UUID, session: AsyncSession):
    exists = await session.scalar(
        select(func.count(DocumentPermission.id))
        .where(
            DocumentPermission.document_id == document_id,
            DocumentPermission.can_view == True,
            or_(
                DocumentPermission.user_id == user_id,
                DocumentPermission.role == user_role
            )
        )
    )
    if not exists:
        raise HTTPException(403, "You do not have permission to view this document")

async def assert_can_download(user_id: UUID, user_role: str, document_id: UUID, session: AsyncSession):
    exists = await session.scalar(
        select(func.count(DocumentPermission.id))
        .where(
            DocumentPermission.document_id == document_id,
            DocumentPermission.can_download == True,
            or_(
                DocumentPermission.user_id == user_id,
                DocumentPermission.role == user_role
            )
        )
    )
    if not exists:
        raise HTTPException(403, "You do not have download permission for this document")
```

---

## Document Download with Watermarking

Every document download goes through the watermark service. Raw file bytes are never streamed to the client directly.

```python
# services/document_service.py

async def stream_watermarked_document(
    document: Document,
    current_user: CurrentUser,
    minio_client: MinioClient
) -> bytes:
    """
    1. Fetch raw bytes from MinIO
    2. Apply watermark via pypdf
    3. Return watermarked bytes for streaming
    """
    raw_bytes = await minio_client.get_object(document.minio_key)
    watermark_text = f"{current_user.full_name}  |  {current_user.email}  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    return apply_watermark(raw_bytes, watermark_text)

def apply_watermark(pdf_bytes: bytes, text: str) -> bytes:
    """
    Uses pypdf to stamp a diagonal grey text watermark on every page.
    The watermark is visible but does not obscure content.
    """
    from pypdf import PdfReader, PdfWriter
    import io

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        # Add watermark annotation to each page
        # Implementation: create a watermark PDF page with reportlab,
        # then merge it onto each page using pypdf merge_page()
        writer.add_page(page)  # see full implementation in services/

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
```

Download endpoint:
```python
@router.get("/deal-rooms/{deal_room_id}/documents/{doc_id}/download")
async def download_document(deal_room_id: UUID, doc_id: UUID, ...):
    doc = await doc_repo.get_by_id(doc_id)   # already membership-gated
    await permission_service.assert_can_download(
        current_user.id, current_user.deal_room_role, doc_id, session
    )
    watermarked = await document_service.stream_watermarked_document(doc, current_user, minio)
    await log_event(session, current_user, AuditAction.DOCUMENT_DOWNLOADED,
                    "document", doc.id, doc.filename, deal_room_id,
                    metadata={"file_size_bytes": doc.file_size_bytes})
    return Response(
        content=watermarked,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'}
    )
```

---

## Audit Trail

### AuditAction Constants

```python
# core/audit.py

class AuditAction:
    # Auth
    USER_LOGIN              = "user.login"
    USER_LOGIN_FAILED       = "user.login_failed"
    USER_INVITED            = "user.invited"

    # Deal room
    DEAL_ROOM_CREATED       = "deal_room.created"
    DEAL_ROOM_ACCESSED      = "deal_room.accessed"
    DEAL_ROOM_ARCHIVED      = "deal_room.archived"

    # Members & permissions
    MEMBER_INVITED          = "permission.member_invited"
    MEMBER_REMOVED          = "permission.member_removed"
    ROLE_CHANGED            = "permission.role_changed"
    DOC_PERMISSION_GRANTED  = "permission.document_granted"
    DOC_PERMISSION_REVOKED  = "permission.document_revoked"
    DOCUMENT_RESTRICTED     = "permission.document_restricted"

    # Documents
    DOCUMENT_UPLOADED       = "document.uploaded"
    DOCUMENT_VIEWED         = "document.viewed"
    DOCUMENT_DOWNLOADED     = "document.downloaded"
    DOCUMENT_DELETED        = "document.deleted"

    # Reports
    REPORT_ANALYSIS_STARTED = "report.analysis_started"
    REPORT_ITEM_EDITED      = "report.item_edited"
    REPORT_SUBMITTED_REVIEW = "report.submitted_for_review"
    REPORT_APPROVED         = "report.approved"
    REPORT_EXPORTED         = "report.exported"

    # Annotations
    ANNOTATION_CREATED      = "annotation.created"
    ANNOTATION_RESOLVED     = "annotation.resolved"
    ANNOTATION_DISPUTED     = "annotation.disputed"

    # Q&A
    QA_GENERATED            = "qa.generated"
    QA_EMAIL_SENT           = "qa.email_sent"
```

### log_event Helper

```python
# core/audit.py

async def log_event(
    session: AsyncSession,
    actor: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    resource_name: str | None = None,
    deal_room_id: UUID | None = None,
    metadata: dict | None = None,
    request: Request | None = None,
):
    """
    Write one audit log entry. Always called before the response is returned.
    Do NOT commit here — caller's transaction commits both the action and the log entry atomically.
    """
    stmt = insert(AuditLog).values(
        tenant_id     = actor.tenant_id,
        deal_room_id  = deal_room_id,
        actor_id      = actor.id,
        actor_email   = actor.email,
        actor_role    = actor.role,
        action        = action,
        resource_type = resource_type,
        resource_id   = resource_id,
        resource_name = resource_name,
        metadata      = metadata or {},
        ip_address    = request.client.host if request else None,
        user_agent    = request.headers.get("user-agent") if request else None,
    )
    await session.execute(stmt)
    # Note: no session.commit() — let the caller's transaction handle it
```

### Usage Pattern in Routers

```python
# Every state-changing endpoint follows this pattern:
@router.post("/deal-rooms/{deal_room_id}/reports/{report_id}/approve")
async def approve_report(deal_room_id: UUID, report_id: UUID, body: ApprovalRequest, ...):
    # 1. Permission check
    await approval_service.assert_can_approve(report_id, current_user, session)
    # 2. State change
    report = await report_repo.approve(report_id, current_user.id, body.sign_off_notes)
    # 3. Audit log (same transaction)
    await log_event(session, current_user, AuditAction.REPORT_APPROVED,
                    "report", report.id, f"Report for {report.deal_room.target_company}",
                    deal_room_id=deal_room_id,
                    metadata={"sign_off_notes": body.sign_off_notes})
    await session.commit()
    return report
```

### Audit Log API Endpoints

```
GET /api/deal-rooms/{id}/audit-log
  Auth: owner or senior_analyst only
  Query params: ?action=&actor_id=&from=&to=&page=&page_size=
  Response: paginated List[AuditLogEntry]
  - Ordered by occurred_at DESC
  - Used for the Activity Log tab in the frontend

GET /api/deal-rooms/{id}/audit-log/export
  Auth: owner only
  Response: CSV download of full deal room audit log
  - Logs: AuditAction.AUDIT_LOG_EXPORTED (yes, the export is itself audited)
```

### Activity Log UI (AuditLog.jsx)

Displayed as a tab inside the Deal Room page.

```
Layout: reverse-chronological feed

Each entry renders as:
  [Avatar/initials] [actor_name] [action_label] [resource_name]
  [occurred_at timestamp]  [IP address]

Examples:
  "Sarah K.  approved report  'Analysis Report — Q1 2025'  3 hours ago  192.168.1.1"
  "James R.  downloaded  'AcmeCorp_Financials_2024.pdf'  yesterday  10.0.0.5"
  "Admin  restricted access to  'Legal_NDA_v2.pdf'  2 days ago"

Filter bar:
  - By team member (dropdown)
  - By action type (multi-select)
  - Date range picker

Export button: downloads CSV (owner only)
```

---

## Security Hardening Checklist

These are production concerns — implement in the capstone where time allows, note on roadmap otherwise.

- [ ] DB user `dealroom_app_user` has `REVOKE DELETE, UPDATE ON audit_log`
- [ ] MinIO bucket policy: `dealroom_app_user` can PUT and GET but not list bucket contents (prevents enumeration)
- [ ] JWT tokens expire in 60 minutes — refresh token pattern for production
- [ ] Failed login attempts logged as `user.login_failed` — rate-limit after 5 failures per IP per hour
- [ ] Document download endpoint rate-limited (100 downloads/hour per user)
- [ ] All `metadata` JSONB fields sanitised — no raw user input stored unescaped
- [ ] Audit log entries include IP address — useful for incident response
