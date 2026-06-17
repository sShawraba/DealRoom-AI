# Phase 8 — Frontend
## tasks.md

- [ ] **Task 01** — Write `api/client.js` (Axios instance with baseURL, JWT interceptor, 401 handler) and all 7 API modules with typed function signatures
- [ ] **Task 02** — Write `hooks/useJobStatus.js`, `hooks/usePolling.js`, `hooks/useAuth.js`, `hooks/useDealRoom.js`
- [ ] **Task 03** — Write `pages/Login.jsx` and `pages/Register.jsx` — forms, loading states, error display, redirect on success
- [ ] **Task 04** — Write `components/layout/Sidebar.jsx` and `Topbar.jsx`. Write `App.jsx` with protected route wrapper (redirect to /login if no token)
- [ ] **Task 05 [needs 01,02,04]** — Write `components/deal-rooms/DealRoomCard.jsx` (colour from RISK_COLORS), `RiskHeatmap.jsx`, `CreateDealRoomModal.jsx`. Write `pages/Dashboard.jsx` with heatmap + create modal + empty state
- [ ] **Task 06 [needs 01,02,05]** — Write `components/documents/DocumentUploader.jsx` (react-dropzone, multipart POST, per-file progress bar), `DocumentList.jsx` (status badges + useJobStatus polling). Install react-dropzone.
- [ ] **Task 07 [needs 06]** — Write `components/members/MemberList.jsx` and `InviteMemberModal.jsx`. Write `pages/DealRoom.jsx` with upload + document list + members panel + missing context panel
- [ ] **Task 08 [needs 01,02]** — Write `components/report/RiskScoreCard.jsx` (score, tier badge, SHAP bars), `CitationPanel.jsx` (right drawer with chunk text), `ApprovalBar.jsx` (status-aware: submit/approve buttons or approved banner with name+date)
- [ ] **Task 09 [needs 08]** — Write `components/report/ReportItem.jsx` (AI content vs edited content, citation link, annotation badge, edit pencil → inline textarea), `ReportSection.jsx` (section header + item list + unresolved count badge)
- [ ] **Task 10 [needs 09]** — Write `components/annotations/AnnotationThread.jsx` (thread with replies, type badges comment/verified/disputed, resolve button), `AnnotationBadge.jsx` (red if disputed)
- [ ] **Task 11 [needs 08,09,10]** — Write `pages/Report.jsx` with three-panel layout, annotation sidebar (15s polling), Q&A panel with generate button + email modal, section nav (sticky left)
- [ ] **Task 12 [needs 01,02]** — Write `components/audit/ActivityFeed.jsx` (event list with filters: user dropdown, action multi-select, date range). Write `pages/AuditLog.jsx` with CSV export button
- [ ] **Task 13 [needs 05]** — Write `components/deal-rooms/CompareModal.jsx` (select second deal room + display comparison side-by-side). Add Compare button to Dashboard.
- [ ] **Task 14 [needs 03,04,05,07,11,12]** — Manual smoke test: all 5 pages load, all empty states visible, login → dashboard → create deal room → upload doc → watch status update → trigger analysis → view report → post annotation → approve report. No white screens at any step.

- [ ] **Task 15 (pagination UI)** — Add a reusable `Pagination.jsx` component: prev/next buttons, current page indicator, total count. Use in: DocumentList, Dashboard deal room list, AuditLog feed, Report list, Q&A list, Annotation thread (load more).
- [ ] **Task 16 (cache admin UI)** — Add a small "Cache" section in the Admin area (owner only): three buttons — "Clear embedding cache for this deal room", "Clear research cache for [company]", "Clear ML cache". Each calls the corresponding DELETE /api/v1/admin/cache/* endpoint and shows a success toast.w
- [ ] **Task 17 — Write hooks/useAnalysisStream.js** — opens EventSource to /api/v1/deal-rooms/{id}/reports/{rid}/stream, dispatches events to state — on section_complete append section to report, on analysis.complete mark done, on analysis.failed show error, cleanup on unmount