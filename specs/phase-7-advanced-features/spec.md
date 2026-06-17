# Phase 7 — Advanced Features
## spec.md

### Overview
Three standalone features built on top of the completed core: deal comparison (side-by-side view of two deal rooms), precedent search (semantic search across a tenant's past deals), and document permission management (restrict/unrestrict individual documents).

### User Stories
- As an analyst, I select two deal rooms and see their risk scores, financial ratios, red flag counts, and key findings side by side.
- As an analyst, I search my firm's past closed deals for ones with similar risk profiles or industries.
- As a senior analyst, I restrict a document to senior analysts and owners only — analysts no longer see its content in reports or retrieval.

### Requirements
- `GET /api/v1/deal-rooms/compare?ids={id1},{id2}` — caller must be a member of BOTH rooms; returns side-by-side object; 404 if not member of either
- Comparison object: `{deal_rooms: [{id, name, target_company, risk_score, risk_tier, red_flag_count, financial_snapshot, top_findings: list[str]}]}`
- `GET /api/v1/deal-rooms/search?q={query}&status=closed` — semantic search over executive_summary embeddings of past reports within tenant; returns ranked list of deal rooms with match score
- `PATCH /api/v1/documents/{doc_id}/permissions` — body `{mode: "default"|"restricted", grants: [{user_id|role, can_view, can_download}]}`; owner or senior_analyst only; deletes existing permissions, inserts new grants, logs `permission.document_restricted`
- `GET /api/v1/documents/{doc_id}/permissions` — owner or senior_analyst only

### Acceptance Criteria
```bash
# Compare two deal rooms → both risk scores in response, red_flag_count correct
# Non-member of one room → 404
# Precedent search "SaaS low margin" → returns relevant past deals
# Restrict document → analyst cannot retrieve its content via RAG
# permissions endpoint returns current grants with user/role info
```
