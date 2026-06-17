# Phase 8 — Frontend
## spec.md

### Overview
Build the complete React 18 frontend: five pages, all components, polling hooks, and the Axios API client with JWT handling. The frontend connects to all backend endpoints built in Phases 1–7.

### Pages & Key Behaviour
- **Login / Register** — auth forms, redirect to dashboard on success
- **Dashboard** — risk heatmap (colour-coded deal room cards), new deal room modal, deal comparison trigger
- **DealRoom** — document upload (drag-and-drop), per-document ARQ status polling (3s while processing), member management panel, missing context display
- **Report** — three-panel layout: section navigation (sticky left), report content (centre), annotation sidebar (right). RiskScoreCard with SHAP bars. CitationPanel drawer. Inline item edit. ApprovalBar (status-aware, shows unresolved disputed count). Q&A panel with email button.
- **AuditLog** — reverse-chronological activity feed, filter by user/action/date, CSV export button

### Requirements
- Zustand auth store: persisted (localStorage), `{token, user, setAuth, logout}`
- Axios interceptor: attaches JWT, handles 401 (clears store + redirect to /login)
- `useJobStatus(jobId, intervalMs=3000)` hook: polls `/api/v1/jobs/{id}/status`, stops when complete/failed
- `usePolling(fn, intervalMs, active)` hook: calls fn every intervalMs while active=true
- Annotation panel polls `GET /api/v1/deal-rooms/{id}/annotations` every 15s
- All list pages have empty states — no blank screens
- All async operations show skeleton loaders — no white screens
- Approved reports: all edit controls hidden, green approved banner at top, export button visible
- Approval button shows tooltip with unresolved dispute count when blocked

### Acceptance Criteria
```bash
# Register → dashboard in < 30s
# Upload PDF → status badge cycles queued → in_progress → ready without refresh
# Report: all 6 sections render with citation links
# Click citation → CitationPanel shows source chunk text
# Post disputed annotation → red badge on section header
# Approve button shows "1 disputed annotation must be resolved" tooltip
# After approval: edit pencil icons hidden, green banner visible, export enabled
# Audit log shows 8+ distinct event types with timestamps
# All pages show skeleton on first load — no blank screens
```
