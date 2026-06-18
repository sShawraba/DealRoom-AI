# Phase 6 — Review & Approval Workflow
## tasks.md

- [X] **Task 01** — Add ENUMs `annotation_type`, `qa_category`, `qa_priority` to `app/models/base.py`. Write annotation, reply, approval, management_question models
- [X] **Task 02 [needs 01]** — Create migration `005_review_workflow.py`: annotations + replies + report_approvals + management_questions tables + all indexes. Index: `annotations(report_item_id)`, `annotations(type, resolved)`, `management_questions(report_id)`
- [X] **Task 03 [needs 01]** — Write `app/repositories/annotation.py`: `AnnotationRepository` with `create()` (checks report not approved), `list_by_deal_room(deal_room_id)` returning dict keyed by report_item_id, `resolve()`, `get_unresolved_disputed_count(report_id)`
- [X] **Task 04 [needs 01]** — Write `app/repositories/management_qa.py`: `ManagementQuestionRepository` with `bulk_insert()` and `list_by_report_grouped(report_id)` returning dict keyed by category
- [X] **Task 05 [needs 03]** — Write `app/services/approval_service.py`: `assert_can_approve()` (role check + disputed count check — both atomic), `approve_report()` (status transition + create ReportApproval row)
- [X] **Task 06** — Write `app/services/email_service.py`: `send_qa_email(to, deal_room_name, questions)` using aiosmtplib + formatted email body, returns sent timestamp
- [X] **Task 07** — Write `app/schemas/annotation.py` and `app/schemas/management_qa.py`
- [X] **Task 08 [needs 03,07]** — Write `app/routers/annotations.py`: POST create (blocked if approved), GET by deal room, PATCH resolve/type, POST reply. All calls log to audit.
- [X] **Task 09 [needs 04,05,06,07]** — Write `app/routers/management_qa.py`: POST generate (LLM call + bulk_insert), GET list, PATCH answer, POST send-email (calls email_service + logs qa.email_sent)
- [X] **Task 10 [needs 05]** — Add to `app/routers/reports.py`: PATCH item edit (blocked if approved, sets edited_content/edited_by/edited_at, logs report.item_edited); POST status (submit_for_review: draft→in_review; approve: calls assert_can_approve + approve_report, logs report.approved)
- [X] **Task 11 [needs 08,09,10]** — Register new routers in `app/main.py`
- [X] **Task 12 [needs 02,05,08,10]** — Write `tests/test_approval.py`: full flow — post dispute → try approve (409) → resolve → approve (200) → verify report_approvals row → try edit item (409) → try post annotation (409). Also: analyst tries approve (403).
- [X] **Task 13 [needs 09]** — Write `tests/test_qa.py`: generate Q&A → verify rows grouped by category → record answer → send email (mock SMTP) → verify audit log has qa.email_sent with recipient
- [X] **Task 14 [needs 12,13]** — Run `pytest tests/test_approval.py tests/test_qa.py -v` — all pass

- [X] **Task 15 (pagination — annotations)** — Update `GET /api/v1/deal-rooms/{id}/annotations` to accept `?page=1&page_size=50` and return `PaginatedResponse[AnnotationResponse]`. The frontend polls this endpoint every 15s — pagination prevents the response growing unbounded as annotations accumulate.
- [X] **Task 16 (pagination — Q&A)** — Update `GET /api/v1/deal-rooms/{id}/reports/{rid}/qa` to return `PaginatedResponse[ManagementQuestionResponse]`. Accept `?page=1&page_size=20&category=financial`.
- [X] **Task 17 (DI check)** — Verify `app/routers/annotations.py` and `app/routers/management_qa.py` inject all dependencies via `Depends()`. No direct session or redis construction.
- [X] **Task 18 (schema check)** — Confirm every Pydantic model used in Phase 6 is in `app/schemas/annotation.py` or `app/schemas/management_qa.py`. Check for any inline `class Foo(BaseModel)` inside router files and move them.

## Content Moderation Tasks
- [X] **Task 19 (moderation on user content)** — In annotation create endpoint: call `await moderate_content(body.content)` before storing. If `result.flagged`: raise `HTTPException(422, f"Content flagged: {result.categories}")`. Apply same check to Q&A answer notes (`PATCH /management-questions/{id}/answer`) and approval sign-off notes. Log `guardrail.content_flagged` with user_id, resource_type, categories (not the content).
