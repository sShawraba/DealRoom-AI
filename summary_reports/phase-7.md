# Phase 7 — Advanced Features Summary

## Files Created / Modified

| File | Action | Description |
|------|--------|-------------|
| `backend/app/routers/comparison.py` | Created | `GET /api/v1/deal-rooms/compare` and `GET /api/v1/deal-rooms/search` with pagination |
| `backend/app/routers/permissions.py` | Created | `PATCH` and `GET /api/v1/documents/{doc_id}/permissions` |
| `backend/app/main.py` | Modified | Registered comparison (before deal_rooms to avoid route conflict) and permissions routers |
| `backend/app/models/document_permission.py` | Modified | Added nullable `role` column; made `user_id` nullable to support role-based grants |
| `backend/app/repositories/report.py` | Modified | Added `get_latest_approved(deal_room_id)` method |
| `backend/app/core/audit.py` | Modified | Added `PERMISSION_DOCUMENT_RESTRICTED` action |
| `backend/migrations/versions/006_document_permission_role.py` | Created | Alembic migration adding `role` column to `document_permissions`, drops old unique constraint |
| `backend/tests/test_advanced.py` | Created | 8 integration tests covering all acceptance criteria |
| `specs/phase-7-advanced-features/tasks.md` | Modified | All 8 tasks marked `[X]` |

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Compare two deal rooms → both risk scores in response, red_flag_count correct | ✓ PASS |
| Non-member of one room → 404 | ✓ PASS |
| Exactly two IDs required → 422 otherwise | ✓ PASS |
| Precedent search "SaaS low margin" → returns relevant past deals | ✓ PASS |
| Restrict document (PATCH mode=restricted) → grants persisted correctly | ✓ PASS |
| Analyst cannot modify permissions → 403 | ✓ PASS |
| Default mode resets permissions to all deal room members | ✓ PASS |
| GET permissions returns current grants | ✓ PASS |

## Test Results

```
8 passed, 32 warnings in 10.06s
```

## Notes

- Comparison router is registered **before** `deal_rooms_router` in `main.py` — necessary so `/compare` and `/search` are not swallowed by the `/{room_id}` wildcard route.
- Precedent search uses pgvector over `document_chunks` (which already has embeddings) rather than `report_items` (which has no embedding column). This avoids a migration and leverages existing indexed vectors.
- Migration 006 also drops the old `uq_doc_permission` unique constraint on `(document_id, user_id)` since role-based rows would violate it (they have `user_id = NULL`).
