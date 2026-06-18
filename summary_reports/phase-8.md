# Phase 8 — Frontend Summary

## Files Created / Modified

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/api/auth.js` | Created | `register()`, `login()` |
| `frontend/src/api/dealRooms.js` | Created | `list()`, `create()`, `get()`, `update()`, `remove()`, `compare()`, `listMembers()`, `addMember()`, `removeMember()`, `updateMember()` |
| `frontend/src/api/documents.js` | Created | `upload()` (multipart with progress), `list()`, `download()`, `remove()` |
| `frontend/src/api/reports.js` | Created | `trigger()`, `list()`, `get()`, `updateItem()`, `changeStatus()`, `approve()` |
| `frontend/src/api/annotations.js` | Created | `create()`, `listByDealRoom()`, `resolve()`, `reply()` |
| `frontend/src/api/managementQA.js` | Created | `generate()`, `list()`, `answer()`, `sendEmail()` |
| `frontend/src/api/audit.js` | Created | `list()`, `exportCSV()` |
| `frontend/src/hooks/usePolling.js` | Created | Generic interval hook with active flag |
| `frontend/src/hooks/useJobStatus.js` | Created | Polls `/jobs/{id}/status`, stops on complete/failed/not_found |
| `frontend/src/hooks/useAuth.js` | Created | Thin wrapper over Zustand auth store |
| `frontend/src/hooks/useDealRoom.js` | Created | Fetches deal room + documents + members in parallel |
| `frontend/src/hooks/useAnalysisStream.js` | Created | EventSource hook for SSE stream, dispatches section_complete / analysis.complete / analysis.failed |
| `frontend/src/pages/Login.jsx` | Created | Email+password form, error display, redirect on success |
| `frontend/src/pages/Register.jsx` | Created | Full registration form (name, email, firm, password) |
| `frontend/src/pages/Dashboard.jsx` | Created | RiskHeatmap + CreateDealRoomModal + CompareModal + Pagination, skeleton loaders |
| `frontend/src/pages/DealRoom.jsx` | Created | Upload + DocumentList + MemberPanel + MissingContext + trigger analysis |
| `frontend/src/pages/Report.jsx` | Created | Three-panel layout: section nav, report content, annotation sidebar (15s polling) + Q&A panel + email modal |
| `frontend/src/pages/AuditLog.jsx` | Created | Activity feed with user/action/date filters + CSV export |
| `frontend/src/App.jsx` | Modified | Protected route wrapper (redirect to /login if no token), 5 routes |
| `frontend/src/components/layout/Sidebar.jsx` | Created | Nav links, tenant name, logout |
| `frontend/src/components/layout/Topbar.jsx` | Created | Breadcrumb header |
| `frontend/src/components/deal-rooms/DealRoomCard.jsx` | Created | Colour-coded by risk_tier (RISK_COLORS), shows score + doc count + disputed |
| `frontend/src/components/deal-rooms/RiskHeatmap.jsx` | Created | Grid of DealRoomCards, empty state |
| `frontend/src/components/deal-rooms/CreateDealRoomModal.jsx` | Created | Modal form: company name + description |
| `frontend/src/components/deal-rooms/CompareModal.jsx` | Created | Select second deal room, display side-by-side risk comparison |
| `frontend/src/components/documents/DocumentUploader.jsx` | Created | react-dropzone, multipart POST, per-file progress bar |
| `frontend/src/components/documents/DocumentList.jsx` | Created | Status badges, useJobStatus polling on in-progress docs |
| `frontend/src/components/members/MemberList.jsx` | Created | Table with role badges, remove button |
| `frontend/src/components/members/InviteMemberModal.jsx` | Created | Email + role selector form |
| `frontend/src/components/report/RiskScoreCard.jsx` | Created | Score, tier badge, SHAP bars (Tailwind width %) |
| `frontend/src/components/report/CitationPanel.jsx` | Created | Right drawer with chunk text + source info |
| `frontend/src/components/report/ApprovalBar.jsx` | Created | Status-aware: submit/approve buttons or approved banner; approve disabled with tooltip when disputed |
| `frontend/src/components/report/ReportItem.jsx` | Created | AI vs edited content, citation link, annotation badge, inline edit |
| `frontend/src/components/report/ReportSection.jsx` | Created | Section header + item list + unresolved dispute count badge |
| `frontend/src/components/annotations/AnnotationThread.jsx` | Created | Thread with replies, type badges, resolve button |
| `frontend/src/components/annotations/AnnotationBadge.jsx` | Created | Count bubble, red if any disputed |
| `frontend/src/components/audit/ActivityFeed.jsx` | Created | Event list, user/action/date filters, skeleton loader |
| `frontend/src/components/Pagination.jsx` | Created | Prev/next + page indicator, used in Dashboard, AuditLog |
| `frontend/src/components/CacheAdmin.jsx` | Created | Three cache-clear buttons (embedding, research, ML) calling `/admin/cache/*` |
| `frontend/package.json` | Modified | Added `react-dropzone` dependency |
| `specs/phase-8-frontend/tasks.md` | Modified | All tasks marked `[X]` (except Task 14 manual smoke test) |

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Login → dashboard redirect | ✓ Implemented |
| Upload PDF → status polling (queued → in_progress → ready) | ✓ useJobStatus polls every 3s, stops on terminal state |
| Report sections render with citation links | ✓ ReportSection + ReportItem with [src] link |
| Click citation → CitationPanel shows source chunk text | ✓ CitationPanel right drawer |
| Post disputed annotation → red badge on section header | ✓ AnnotationBadge red when disputed + unresolved |
| Approve button shows tooltip with unresolved dispute count | ✓ ApprovalBar `title` attribute + disabled |
| After approval: edit pencils hidden, green banner, export enabled | ✓ isApproved guards all edit controls |
| Audit log shows event types with timestamps | ✓ ActivityFeed with action color badges |
| All pages show skeleton on first load | ✓ Skeleton components in Dashboard, DealRoom, Report |

## Notes

- **Build**: `vite build` completes cleanly (no errors, 336 kB bundle).
- **Audit log**: The backend has no `GET /api/v1/audit-log` endpoint yet. The AuditLog page calls it; it will gracefully show an empty state with a 404 until Phase 9 adds the endpoint.
- **Task 14** (manual smoke test) requires the full Docker stack running — left for manual verification.
- **CacheAdmin** component is self-contained and can be embedded in any owner-only admin panel in Phase 9.
- **RISK_COLORS** map is exported from `DealRoomCard.jsx` and reused in `RiskScoreCard.jsx` and `CompareModal.jsx`.
