# Phase 6 — Review & Approval Workflow
## spec.md

### Overview
Build the full collaborative review and approval system. Junior analysts annotate report findings. Senior analysts resolve disputes, edit items, and approve. Approval is blocked until all disputed annotations are resolved — enforced atomically at the API layer. Approved reports are permanently read-only at the repository layer. Management Q&A is generated from report findings and can be emailed to the target company.

### User Stories
- As an analyst, I can post a comment, verification, or dispute flag on any report finding.
- As an analyst, I can reply to an existing annotation to create a thread.
- As an analyst, I submit the report for review when I'm done annotating.
- As a senior analyst, I can edit any report item's text (original AI content preserved separately).
- As a senior analyst, I cannot approve until all disputed annotations are resolved — the API returns 409 with a count.
- As a senior analyst, I approve the report — it becomes permanently read-only with my name and timestamp attached.
- As an analyst, I generate a Q&A list from the report and send it to the target company by email.

### Requirements
**Annotations**
- `POST /api/v1/report-items/{item_id}/annotations` — blocked if report is approved (409)
- `GET /api/v1/deal-rooms/{id}/annotations` — all annotations for the deal room, keyed by report_item_id
- `PATCH /api/v1/annotations/{id}` — resolve or change type
- `POST /api/v1/annotations/{id}/replies`

**Approval Workflow**
- `POST /api/v1/deal-rooms/{id}/reports/{rid}/status` — body `{action: "submit_for_review"|"approve"}`
  - `submit_for_review`: any analyst, draft → in_review
  - `approve`: owner or senior_analyst only; checks zero unresolved disputed annotations atomically; in_review → approved; creates `report_approvals` row
- After approval: ALL mutations on report_items and annotations return 409

**Report Item Edit**
- `PATCH /api/v1/deal-rooms/{id}/reports/{rid}/items/{item_id}` — body `{edited_content: str}`; blocked if approved; sets `edited_content`, `edited_by`, `edited_at`

**Management Q&A**
- `POST /api/v1/deal-rooms/{id}/reports/{rid}/qa/generate` — single LLM call over red_flags + financial_health + legal_flags items; persists to `management_questions` table
- `GET /api/v1/deal-rooms/{id}/reports/{rid}/qa`
- `PATCH /api/v1/management-questions/{id}/answer` — record management's response
- `POST /api/v1/deal-rooms/{id}/reports/{rid}/qa/send-email` — format + send via aiosmtplib; log `qa.email_sent` with recipient

**Audit Events** (all state changes)
`annotation.created`, `annotation.resolved`, `annotation.disputed`, `report.item_edited`, `report.submitted_for_review`, `report.approved`, `report.exported`, `qa.generated`, `qa.email_sent`

### Acceptance Criteria
```bash
# Post disputed annotation → annotation.type = "disputed"
# Try approve with unresolved dispute → 409 {"detail": "1 disputed annotation(s) must be resolved"}
# Resolve dispute → approve succeeds → report_approvals row created
# PATCH report item after approval → 409
# POST annotation after approval → 409
# Generate Q&A → management_questions rows created grouped by category
# Send Q&A email → audit log has qa.email_sent with recipient address
```
