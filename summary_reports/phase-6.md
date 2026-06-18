# Phase 6 — Review & Approval Workflow — Summary Report

**Date:** 2026-06-18  
**Status:** ✅ Complete — 8/8 tests passing

## Files Created

| File | Purpose |
|------|---------|
| `backend/app/models/annotation.py` | Annotation, AnnotationReply models |
| `backend/app/models/report_approval.py` | ReportApproval model |
| `backend/app/models/management_qa.py` | ManagementQuestion model |
| `backend/migrations/versions/005_review_workflow.py` | DB migration: new ENUMs + 4 tables + edit columns |
| `backend/app/repositories/annotation.py` | AnnotationRepository |
| `backend/app/repositories/management_qa.py` | ManagementQuestionRepository |
| `backend/app/services/approval_service.py` | assert_can_approve(), approve_report() |
| `backend/app/services/email_service.py` | send_qa_email() via aiosmtplib |
| `backend/app/schemas/annotation.py` | Annotation + Reply Pydantic schemas |
| `backend/app/schemas/management_qa.py` | ManagementQuestion Pydantic schemas |
| `backend/app/routers/annotations.py` | POST/GET/PATCH/reply annotation endpoints |
| `backend/app/routers/management_qa.py` | POST generate, GET list, PATCH answer, POST send-email |
| `backend/tests/test_approval.py` | Full approval workflow integration tests (4 tests) |
| `backend/tests/test_qa.py` | Q&A generation + email integration tests (4 tests) |

## Files Modified

| File | Change |
|------|--------|
| `backend/app/models/base.py` | Added annotation_type, qa_category, qa_priority ENUMs |
| `backend/app/models/report.py` | Added in_review/approved status; edited_content/by/at on ReportItem |
| `backend/app/schemas/report.py` | Added edited_content/by/at to ReportItemResponse; ReportItemEditBody + ReportStatusBody schemas |
| `backend/app/core/audit.py` | Added REPORT_ITEM_EDITED, REPORT_EXPORTED, QA_GENERATED, QA_EMAIL_SENT, GUARDRAIL_CONTENT_FLAGGED |
| `backend/app/routers/reports.py` | Added PATCH item edit + POST status (submit_for_review / approve) endpoints |
| `backend/app/main.py` | Registered 4 new routers |

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| Post disputed annotation → type = "disputed" | ✅ test_full_approval_flow |
| Try approve with unresolved dispute → 409 | ✅ test_full_approval_flow |
| Resolve dispute → approve succeeds → report_approvals row created | ✅ test_full_approval_flow |
| PATCH report item after approval → 409 | ✅ test_full_approval_flow |
| POST annotation after approval → 409 | ✅ test_full_approval_flow |
| Analyst tries approve → 403 | ✅ test_full_approval_flow |
| Generate Q&A → management_questions rows by category | ✅ test_generate_qa |
| Send Q&A email → audit log has qa.email_sent with recipient | ✅ test_send_qa_email_and_audit_log |

## Key Design Decisions

- **Approval atomicity**: `assert_can_approve()` checks role AND unresolved disputes in the same transaction before setting report status
- **Read-only enforcement**: Done at the repository layer (`_assert_report_not_approved`) + at the router layer for item edits
- **source_item_id validation**: LLM responses validated against actual report item IDs before insert (prevents FK violations from hallucinated UUIDs)
- **Content moderation**: Applied to annotation content, reply content, Q&A answer notes, and approval sign-off notes; all log to `guardrail.content_flagged`
- **Pagination**: Annotations paginated at 50/page; Q&A paginated at 20/page with optional category filter
