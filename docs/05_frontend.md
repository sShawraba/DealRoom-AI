# DealRoom AI — Frontend Spec

## Stack

- React 18 + Vite
- Tailwind CSS (utility classes only)
- React Router v6
- Axios (with JWT interceptor)
- Zustand (auth state only — keep it minimal)
- Lucide React (icons)

---

## Route Structure

```jsx
// App.jsx
<Routes>
  <Route path="/login"    element={<Login />} />
  <Route path="/register" element={<Register />} />
  <Route element={<ProtectedLayout />}>  {/* checks auth, shows sidebar */}
    <Route path="/"                              element={<Dashboard />} />
    <Route path="/deal-rooms/:id"                element={<DealRoom />} />
    <Route path="/deal-rooms/:id/reports/:rid"   element={<Report />} />
  </Route>
</Routes>
```

---

## Auth Store (Zustand)

```js
// store/authStore.js
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(persist(
  (set) => ({
    token: null,
    user: null,    // { id, tenant_id, role, full_name }
    setAuth: (token, user) => set({ token, user }),
    logout: () => set({ token: null, user: null })
  }),
  { name: 'auth-storage' }
))
```

---

## API Client

```js
// api/client.js
import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000'
})

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
```

---

## Pages

### Login.jsx

```
Layout: centered card on white/light gray background
Fields:
  - Email (type="email")
  - Password (type="password")
  - Submit button "Sign in"
  - Link: "Don't have an account? Register"
On submit:
  - POST /api/auth/login
  - On success: setAuth(token, user), redirect to /
  - On error: show inline error message
```

### Register.jsx

```
Layout: centered card
Fields:
  - Full name
  - Work email
  - Password
  - Firm / Company name (creates tenant)
  - Submit "Create account"
On submit:
  - POST /api/auth/register
  - On success: setAuth(token, user), redirect to /
```

### Dashboard.jsx

```
Layout: Sidebar + main content area

Main content:
  Section 1 — Risk Heatmap
    - Fetch GET /api/deal-rooms
    - Render DealRoomCard for each deal room
    - Cards are color-coded by risk_tier:
        low      → green border + badge
        medium   → yellow
        high     → orange
        critical → red
        null     → gray (no analysis run yet)
    - Each card shows:
        deal room name, target company, document count,
        unresolved annotation count, risk score (if available)
    - Click navigates to /deal-rooms/:id

  Section 2 — Action bar
    - "New Deal Room" button → opens CreateDealRoomModal

CreateDealRoomModal:
  Fields: name, target_company, description (optional)
  POST /api/deal-rooms
  On success: close modal, refresh deal room list
```

### DealRoom.jsx

```
Layout: two-column — left: document panel, right: deal room info + actions

Left panel: Document Management
  - DocumentUploader:
      Drag-and-drop zone OR file picker
      Accepts: .pdf, .docx, .xlsx
      On drop: POST /api/deal-rooms/:id/documents (multipart)
      Shows upload progress bar per file

  - DocumentList:
      Fetches GET /api/deal-rooms/:id/documents
      Polls every 10s while any document has status != 'indexed'
      Each row shows: filename, status badge, doc_type, page_count
      Status badges:
        uploaded    → gray "Uploaded"
        processing  → blue spinning "Processing"
        indexed     → green "Ready"
        failed      → red "Failed" + hover tooltip with error_message

Right panel:
  - Deal room name + target company
  - Status badge
  - "Run Analysis" button
      Disabled if: any document is still processing OR status != 'uploaded/indexed'
      On click: POST /api/deal-rooms/:id/reports
      On success: navigate to /deal-rooms/:id/reports/:report_id
  - Previous reports list (if any)
```

### Report.jsx

```
Layout: three-panel
  Left sidebar:  section navigation (sticky)
  Center:        report content
  Right sidebar: annotation panel (slides in on item click)

Center — Report Content:

  Top bar:
    - Deal room name + target company
    - Report status badge (Draft / In Review / Approved)
    - ApprovalBar:
        If status=draft and role=analyst:    "Submit for Review" button
        If status=in_review and role=admin:  "Approve Report" button + sign-off notes textarea
        If status=approved:                  Green "Approved by [name] on [date]" banner
    - "Generate Q&A" button (appears after report loads)
    - "Export" button (only enabled when status=approved)

  RiskScoreCard:
    - Displayed at top of report
    - Large number: risk_score (0-100)
    - Color-coded tier badge
    - Three SHAP factors as horizontal bar chart:
        Each bar shows feature name, direction arrow, magnitude
        Red bars = increases risk, Green bars = decreases risk

  Report sections (in order):
    executive_summary, financial_health, legal_flags,
    commercial_assessment, red_flags, key_questions

  Each section renders as:
    <ReportSection title="Financial Health">
      <ReportItem item={item} /> (for each item)
    </ReportSection>

ReportItem:
  - Displays: edited_content if set, otherwise content (AI original)
  - If edited: show subtle "(edited)" tag next to content
  - Citation link at bottom: "[filename.pdf, p.12]" — clicking opens CitationPanel
  - Right edge: AnnotationBadge (count bubble, color = red if disputed)
  - Hover: "Add comment" icon appears
  - If status != approved AND role in [admin, analyst]:
      "Edit" pencil icon → inline textarea edit
      On save: PATCH /api/deal-rooms/:id/reports/:rid/items/:iid

Annotation Right Panel:
  - Opens when annotation badge or "Add comment" is clicked
  - Shows annotation thread for that report item
  - Each annotation:
      Author name + timestamp
      Type badge: comment (gray) | verified (green) | disputed (red)
      Content
      Reply thread (indented)
      "Resolve" button (for admin/analyst)
  - New annotation input at bottom:
      Textarea + type selector + "Post" button
      POST /api/report-items/:item_id/annotations
  - Panel polls GET /api/deal-rooms/:id/annotations every 15s

CitationPanel:
  - Side drawer (right)
  - Shows source document name + page number
  - Shows the raw chunk text the claim was derived from
  - "View document" link

Management Q&A Panel:
  - Appears below report after "Generate Q&A" is clicked
  - POST /api/deal-rooms/:id/reports/:rid/qa/generate
  - Shows questions grouped by category (financial, legal, operational, strategic)
  - Each question shows priority badge + link icon back to source finding
  - "Record Answer" inline button → opens textarea to fill answer_notes
    PATCH /api/management-questions/:qid/answer
```

---

## Polling Hook

```js
// hooks/usePolling.js
import { useEffect, useRef } from 'react'

export function usePolling(fn, intervalMs = 15000, active = true) {
  const savedFn = useRef(fn)

  useEffect(() => { savedFn.current = fn }, [fn])

  useEffect(() => {
    if (!active) return
    const id = setInterval(() => savedFn.current(), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs, active])
}
```

Usage:
```js
// In DealRoom.jsx — poll document status while processing
const hasProcessing = documents.some(d => d.status === 'processing' || d.status === 'uploaded')
usePolling(fetchDocuments, 10000, hasProcessing)

// In Report.jsx — poll annotations
usePolling(fetchAnnotations, 15000, true)
```

---

## Tailwind Color Conventions

```js
// Use these consistently across components
const RISK_COLORS = {
  low:      { bg: 'bg-green-50',  border: 'border-green-400',  text: 'text-green-700',  badge: 'bg-green-100' },
  medium:   { bg: 'bg-yellow-50', border: 'border-yellow-400', text: 'text-yellow-700', badge: 'bg-yellow-100' },
  high:     { bg: 'bg-orange-50', border: 'border-orange-400', text: 'text-orange-700', badge: 'bg-orange-100' },
  critical: { bg: 'bg-red-50',    border: 'border-red-400',    text: 'text-red-700',    badge: 'bg-red-100' },
  null:     { bg: 'bg-gray-50',   border: 'border-gray-300',   text: 'text-gray-500',   badge: 'bg-gray-100' },
}

const STATUS_COLORS = {
  draft:      'bg-gray-100 text-gray-600',
  in_review:  'bg-blue-100 text-blue-700',
  approved:   'bg-green-100 text-green-700',
}

const ANNOTATION_COLORS = {
  comment:  'bg-gray-100 text-gray-600',
  verified: 'bg-green-100 text-green-700',
  disputed: 'bg-red-100 text-red-600',
}
```

---

## Key UX Rules

1. **Never block the UI** — uploads and analysis run in background. Return immediately, poll for status.
2. **Approved reports are visually locked** — all edit buttons hidden, "read-only" banner at top.
3. **Disputed annotations bubble up** — section headers show red badge count if any disputed items exist within.
4. **Empty states** — every list has a meaningful empty state (not just blank space):
   - No deal rooms: "Create your first deal room to get started"
   - No documents: "Upload documents to begin analysis"
   - No annotations: "No comments yet — click any finding to add one"
5. **Loading states** — all async operations show skeleton loaders or spinners, not blank space.
