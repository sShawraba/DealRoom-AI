# Phase 8 — Frontend
## plan.md

### File Map
```
frontend/src/
  pages/
    Login.jsx           email + password form, POST /auth/login
    Register.jsx        name + email + password + firm form, POST /auth/register
    Dashboard.jsx       deal room list + RiskHeatmap + CreateDealRoomModal + CompareButton
    DealRoom.jsx        DocumentUploader + DocumentList + MemberPanel + MissingContextPanel
    Report.jsx          three-panel: SectionNav + ReportContent + AnnotationSidebar
    AuditLog.jsx        ActivityFeed + filters + CSV export
  components/
    layout/
      Sidebar.jsx       nav links, tenant name, logout
      Topbar.jsx        deal room name breadcrumb
    deal-rooms/
      DealRoomCard.jsx  colour-coded by risk_tier, shows doc count + unresolved annotations
      RiskHeatmap.jsx   grid of DealRoomCards
      CreateDealRoomModal.jsx
      CompareModal.jsx  select second deal room + show comparison
    documents/
      DocumentUploader.jsx  react-dropzone, POST multipart, shows per-file progress
      DocumentList.jsx      per-doc status badge, polling via useJobStatus
    members/
      MemberList.jsx    table of members with role badges
      InviteMemberModal.jsx
    report/
      ReportSection.jsx   section header + item list
      ReportItem.jsx      content (edited or AI), citation link, annotation badge, edit pencil
      RiskScoreCard.jsx   large score, tier badge, 3 SHAP bars (Tailwind width%)
      CitationPanel.jsx   right drawer, chunk text + source info
      ApprovalBar.jsx     status-aware: shows submit/approve buttons or approved banner
      MissingContext.jsx  list of gaps with section labels
    annotations/
      AnnotationThread.jsx  thread of annotations + replies
      AnnotationBadge.jsx   count bubble, red if any disputed
    audit/
      ActivityFeed.jsx    event list with actor, action, resource, timestamp, IP
  hooks/
    useAuth.js          reads from Zustand store
    useJobStatus.js     polls /jobs/{id}/status, stops on complete/failed
    usePolling.js       generic interval hook with active flag
    useDealRoom.js      fetches deal room + documents + members
  api/
    auth.js             register(), login()
    dealRooms.js        list(), create(), get(), update(), delete(), compare()
    documents.js        upload(), list(), download(), delete()
    reports.js          trigger(), list(), get(), updateItem(), changeStatus(), approve()
    annotations.js      create(), listByDealRoom(), resolve(), reply()
    managementQA.js     generate(), list(), answer(), sendEmail()
    audit.js            list(), exportCSV()
```

### Risk Tier Colours (Tailwind classes)
```js
const RISK_COLORS = {
  low:      { border: 'border-green-400',  bg: 'bg-green-50',  text: 'text-green-700',  badge: 'bg-green-100' },
  medium:   { border: 'border-yellow-400', bg: 'bg-yellow-50', text: 'text-yellow-700', badge: 'bg-yellow-100' },
  high:     { border: 'border-orange-400', bg: 'bg-orange-50', text: 'text-orange-700', badge: 'bg-orange-100' },
  critical: { border: 'border-red-400',    bg: 'bg-red-50',    text: 'text-red-700',    badge: 'bg-red-100' },
  null:     { border: 'border-gray-300',   bg: 'bg-gray-50',   text: 'text-gray-500',   badge: 'bg-gray-100' },
}
```

### SHAP Bar Component (no chart library)
```jsx
// Width % = magnitude / max_magnitude * 100
// Background: red if increases_risk, green if decreases_risk
<div className="flex items-center gap-2">
  <span className="text-xs w-24 truncate">{factor.feature}</span>
  <div className={`h-3 rounded ${factor.direction === 'increases_risk' ? 'bg-red-400' : 'bg-green-400'}`}
       style={{width: `${(factor.magnitude / maxMagnitude) * 100}%`}} />
  <span className="text-xs text-gray-500">{factor.direction === 'increases_risk' ? '↑' : '↓'}</span>
</div>
```

---