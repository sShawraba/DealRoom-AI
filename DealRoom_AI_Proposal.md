DealRoom AI
AI-Powered Due Diligence for Consulting Teams
Multi-Tenant SaaS · Agentic AI · ML Risk Scoring · VDR-Grade Access Controls
SUBMITTED BY
AI Engineering Bootcamp — 2026
SE Factory, Beirut Digital District
Capstone Project · Final Proposal v2.0
June 2026
CONFIDENTIAL

DealRoom AI
AI-Powered Due Diligence for Consulting Teams
Multi-Tenant SaaS · Agentic AI · ML Risk Scoring · VDR-Grade Access Controls
SUBMITTED BY
AI Engineering Bootcamp — 2026
SE Factory, Beirut Digital District
Capstone Project · Final Proposal v2.0
June 2026
CONFIDENTIAL

DealRoom AI — Capstone Project Proposal | 2026
Table of Contents
Table of Contents . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
1.1 Definition . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
1.2 Types of Due Diligence . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
1.3 The Traditional Workflow . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
2.1 Labour-Intensive and Expensive . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
2.2 Slow and Deadline-Sensitive . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
2.3 Inconsistent Quality . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
2.4 Institutional Memory Is Trapped . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
3.1 Overview . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
3.2 Key Value Propositions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
5.1 Technology Stack . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12
5.2 Multi-Tenancy Model . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
5.3 End-to-End Data Flow . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
6.1 Document Ingestion Agent . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
6.2 Research Agent . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
6.3 Synthesis Agent . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
6.4 Supporting AI Calls (Lightweight) . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
7.1 RAG Pipeline Architecture . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
7.2 ML Financial Risk Classifier . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
Page 3 Confidential

DealRoom AI — Capstone Project Proposal | 2026
Features . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
Model & Explainability . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 18
8.1 Three-Layer Access Control . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
Layer 1 — Tenant Isolation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
Layer 2 — Deal Room Membership . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
Layer 3 — Document-Level Permissions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
8.2 Document Watermarking . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
8.3 Audit Trail . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20
Audited Events . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20
9.1 Task Queue (ARQ) . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 21
9.2 Three Redis Caches . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 21
Embedding Cache Detail . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 21
Research Cache Detail . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22
Week 1 — Foundation, Access Controls & Core Pipeline . . . . . . . . . . . . . . . . . . . . . 24
Week 2 — Synthesis, Review Workflow & Polish . . . . . . . . . . . . . . . . . . . . . . . . . . 24
12.1 Alignment to Practice Areas . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
12.2 Technical Signals That Stand Out . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
Page 4 Confidential

DealRoom AI — Capstone Project Proposal | 2026
01 Understanding Due Diligence
1.1 Definition
Due diligence is the structured investigative process a buyer, investor, or strategic partner conducts before
completing a significant business transaction. Most commonly associated with mergers and acquisitions (M&A),
private equity investments, and venture capital rounds, it is the mechanism through which one party independently
verifies the representations made by another — surfacing hidden risks, validating financial health, and building the
evidentiary basis for a final go/no-go decision, pricing, and transaction terms.
Due diligence answers three questions: Is the target what it claims to be? What material risks are we taking
on? And is the agreed price appropriate given what we have found?
1.2 Types of Due Diligence
Type Scope Key Deliverable
Financial DD Historical P&L;, balance sheet, cash flow, revenue Normalised financials + quality
quality, working capital, debt structure, of earnings report
off-balance-sheet items
Legal DD Contracts, litigation, IP ownership, regulatory Legal risk register + red flag
compliance, employment agreements, memo
change-of-control clauses
Commercial DD Market sizing, competitive landscape, customer Market and competitive
concentration, pricing power, growth assumptions assessment
Operational DD Business processes, technology infrastructure, Operational risk summary
supply chain, key personnel dependencies
Tax DD Historical filings, tax liabilities, deferred taxes, transfer Tax exposure report
pricing, tax structure optimisation
Technical DD For technology companies: code quality, architecture, Technical assessment memo
security posture, technical debt, IP originality
1.3 The Traditional Workflow
A typical mid-market M&A transaction follows a process that has changed little in two decades:
Page 5 Confidential

DealRoom AI — Capstone Project Proposal | 2026
(cid:127) The target company uploads 500 to 2,000 documents to a Virtual Data Room (VDR) — a secure document
repository.
(cid:127) The buy-side firm assigns 2 to 8 junior analysts to manually review every document, extract key information, and
populate tracking spreadsheets.
(cid:127) Analysts flag anomalies and red flags, which are escalated to senior staff for interpretation.
(cid:127) A manager or director synthesises findings into a due diligence report of 40 to 120 pages covering each
workstream.
(cid:127) The report informs the final offer price, representations and warranties, and whether to proceed at all.
The timeline from data room opening to final report is typically four to eight weeks. On larger transactions this can extend to
twelve weeks.
Page 6 Confidential

DealRoom AI — Capstone Project Proposal | 2026
02 The Problem
Despite being one of the highest-stakes, highest-value activities in corporate finance, the due diligence process
remains almost entirely manual. Before any major acquisition or investment, the buying party must investigate the
target company thoroughly — reviewing hundreds of documents covering financials, legal contracts, and market
data. Today, consulting firms assign teams of junior analysts to do this by hand. They spend weeks reading
thousands of pages, copying figures into spreadsheets, and assembling reports. The quality depends entirely on
who is reviewing on a given day, under whatever deadline pressure they happen to be facing.
2.1 Labour-Intensive and Expensive
Junior analysts at Big 4 and boutique advisory firms bill between $150 and $400 per hour. A single mid-market
deal engagement involves 2,000 to 8,000 analyst-hours of document review. The total cost to clients for DD alone
on a $100M transaction routinely exceeds $500,000 — and on larger deals, well over $2 million. The majority of
that spend goes to work that is fundamentally repetitive: reading documents, extracting figures, and populating
templates.
2.2 Slow and Deadline-Sensitive
M&A transactions run on tight timelines. A bidder that can produce preliminary findings in two days has a structural
advantage over one that takes two weeks. Delays in due diligence extend deal timelines, increase the risk of
leaks, and in competitive auction processes, cost mandates entirely. The current manual process has no
meaningful mechanism for acceleration beyond adding more junior staff.
2.3 Inconsistent Quality
With multiple analysts working in parallel across different document types, the quality and depth of review varies
by individual. Critical clauses in a contract may be read closely by one analyst and skimmed by another working
under time pressure. There is no systematic enforcement of a consistent analytical framework. Red flags that are
obvious in hindsight are frequently missed.
2.4 Institutional Memory Is Trapped
Every completed DD report is a dense repository of pattern-matching expertise. Yet this knowledge is locked
inside completed report PDFs, siloed by deal team, and largely inaccessible when the next deal begins. Junior
analysts start from scratch on every engagement.
Page 7 Confidential

DealRoom AI — Capstone Project Proposal | 2026
Consulting firms deliver high-cost, time-intensive DD reports that are only as good as the attention span of a
junior analyst working 14-hour days under deadline pressure. The knowledge that could make the next
report better sits inert in a filing system.
Page 8 Confidential

DealRoom AI — Capstone Project Proposal | 2026
03 The Solution — DealRoom AI
3.1 Overview
DealRoom AI is a multi-tenant SaaS platform that transforms the due diligence process by combining agentic AI,
retrieval-augmented generation (RAG), and classical machine learning into a collaborative deal intelligence
workspace. Each consulting firm operates within a fully isolated tenant environment. Within that environment,
every M&A transaction gets its own Deal Room — a secure, AI-powered workspace where documents are
uploaded to MinIO object storage, automatically analysed by three specialist AI agents, and synthesised into a
structured due diligence report with full source citations and ML-based financial risk scoring.
The report moves through a governed review workflow: a junior analyst reviews and annotates, a senior analyst
edits, resolves all disputed findings, and provides final sign-off before the report can be exported or the Q&A sent
to the target company. Every action from first login to final export is written to an append-only audit trail — the
same standard expected of enterprise-grade VDR platforms.
What currently takes a team of analysts 2 to 3 weeks of manual review, DealRoom AI produces as a
structured, cited, risk-scored brief in under 10 minutes — with full source traceability back to the original
documents.
3.2 Key Value Propositions
Capability What It Replaces Improvement
Document intelligence Manual document review by junior Hours to seconds per document
analysts
Agentic market research Analyst web browsing + manual Consistent, structured, cited
notes
ML risk scoring Senior analyst gut-feel on financial Reproducible, auditable, explainable
ratios
Structured report synthesis Junior analyst writing from notes Consistent format, zero blank-page
problem
Annotation & review Email threads and comment Threaded, role-gated, in-context
spreadsheets
Approval workflow Ad-hoc sign-off via email Named, timestamped, dispute-gated
Audit trail No record of document access Full VDR-grade activity log
Page 9 Confidential

DealRoom AI — Capstone Project Proposal | 2026
04 Platform Features
01 Deal Dashboard
A central view of all deal rooms — active, in review, and closed — showing each deal's risk tier as a
colour-coded card (green / yellow / orange / red). At a glance: document counts, unresolved annotation
counts, workflow status, and last activity. Immediately surfaces which deals need attention.
02 Document Management & Mid-Process Uploads
Upload PDFs, spreadsheets, and contracts at any point in a deal. Documents are stored in MinIO object
storage (S3-compatible). The ingestion agent processes new uploads automatically via an ARQ background
worker, updating the deal room knowledge base without interrupting ongoing analysis.
03 Annotations & Collaborative Review
Any team member can attach a comment, verification, or dispute flag to any individual report finding.
Annotations support threaded replies. Section headers show unresolved count badges. Disputed items
surface as red badges visible to all team members in the deal room.
04 Senior Analyst Approval Workflow
Reports progress through three enforced stages: Draft, In Review, and Approved. Only a Senior Analyst or
Owner can approve. Approval is blocked until every disputed annotation is resolved — enforced at the API
layer, not just the UI. Once approved, the report is permanently read-only and carries a named sign-off with
timestamp.
05 Deal Comparison View
Select any two deal rooms and compare them side by side: ML risk scores, financial ratios, red flag counts,
and key findings. Particularly useful for PE firms evaluating multiple acquisition targets simultaneously, or for
benchmarking a new deal against a closed precedent.
06 Missing Context Generator
After ingestion, the platform identifies gaps in the uploaded documents — missing financial periods, absent
contracts, incomplete management data — and generates a structured list of what to request from the client.
Each missing item is linked to the report section it would inform.
07 Management Q&A; Generation
Convert red flags and financial anomalies into a structured, priority-ranked list of questions for target
management — grouped by category (financial, legal, operational, strategic). Each question links back to the
specific finding that triggered it, with source citation.
Page 10 Confidential

DealRoom AI — Capstone Project Proposal | 2026
08 Email Q&A; to Client
Send the management Q&A; list directly to the target company from within the platform. The email is
pre-formatted, includes the deal room name and list of prioritised questions, and is logged to the deal room
audit trail. Recipient and sent timestamp are recorded permanently.
Page 11 Confidential

DealRoom AI — Capstone Project Proposal | 2026
05 System Architecture
5.1 Technology Stack
Layer Technology Reason
Frontend React 18 (Vite) + Tailwind CSS + Fast SPA; component-based; Tailwind for
React Router v6 consistent design system
Backend FastAPI (Python 3.12) Async-native; typed; auto-generated OpenAPI
docs; integrates cleanly with LangGraph and
scikit-learn
Database PostgreSQL 16 + pgvector extension Relational integrity for multi-tenant data; pgvector
for embedding storage and ANN search in the
same instance
File Storage MinIO (S3-compatible object storage) Files never stored in PostgreSQL; only the object
key is persisted; swap to AWS S3 in prod with
one config change
Task Queue Redis + ARQ (async task queue) Long-running jobs (ingestion, analysis) survive
server restarts; retry on failure; independent
worker scaling
Cache Redis (embedding, research, ML Reduces OpenAI API costs 15-30%; avoids
inference) re-running the research ReAct loop for repeated
companies
Auth JWT (python-jose) + bcrypt (passlib) Standard; stateless; tenant_id and deal room role
encoded in token; secrets in vault
Agents LangGraph + LangChain Graph-based orchestration; stateful ReAct loops;
full state management and conditional branching
LLM GPT-4o / Claude Sonnet Abstracted behind provider interface — model
(OpenAI-compatible API) swappable without code changes
Embeddings OpenAI text-embedding-3-small (1536 Strong retrieval performance; cost-efficient;
dims) cached in Redis
ML Framework scikit-learn + XGBoost + SHAP XGBoost for financial risk classification; SHAP for
per-prediction explainability
Observability LangSmith Full trace of every agent run, tool call, LLM
prompt, token cost, and latency
Page 12 Confidential

DealRoom AI — Capstone Project Proposal | 2026
Layer Technology Reason
Email aiosmtplib (async SMTP) Q&A; dispatch directly from platform; sent emails
logged to audit trail
Watermarking pypdf User name + timestamp stamped on every
downloaded document before streaming
Containers Docker + Docker Compose Full stack in one docker compose up;
reproducible environments
CI/CD GitHub Actions Backend tests, ML eval gate, and prompt
regression on every push
5.2 Multi-Tenancy Model
Tenant isolation is enforced at three layers, each independent:
(cid:127) Database layer: Every table carries a tenant_id column. All queries run through a BaseTenantRepository that
automatically appends .filter(tenant_id == current_tenant). A query that skips this cannot be written without
explicitly overriding the base class.
(cid:127) Deal room layer: Being in a tenant does not grant access to any deal room. Every deal room query joins
through the deal_room_members table. A user not explicitly invited receives a 404 — not a 403 — so they
cannot infer the room exists.
(cid:127) Document layer: Every document has an ACL in document_permissions. The pgvector retrieval query joins
through this table before the similarity operator runs — agents never surface content a user is not permitted to
see.
(cid:127) MinIO: Object paths are prefixed with tenant_id, making cross-tenant file access structurally impossible
regardless of application logic.
5.3 End-to-End Data Flow
A complete analysis run proceeds as follows:
1 Upload User uploads documents via the React frontend. Files stream directly to MinIO.
Document metadata is written to PostgreSQL. An ARQ job is enqueued in Redis.
2 Ingestion The ARQ worker picks up the job and runs the Document Ingestion Agent: parse
PDF with pdfplumber, extract tables as atomic chunks, classify document type,
generate embeddings (with Redis cache), write chunks to pgvector.
3 Analysis Trigger Analyst clicks Analyse. Backend validates all documents are indexed, creates a
report row, enqueues task_run_analysis in Redis.
Page 13 Confidential

DealRoom AI — Capstone Project Proposal | 2026
4 Research ARQ worker runs the Research Agent ReAct loop — up to 12 tool calls across web
search, financial data, news sentiment, and competitor lookup. Results cached in
Redis for 24 hours.
5 ML Scoring Financial ratios are extracted from chunks (or entered manually). XGBoost
classifier returns a risk score (0–100), risk tier, and top 3 SHAP-attributed features.
Result cached in Redis.
6 Synthesis Synthesis Agent runs per-section hybrid retrieval (pgvector cosine + BM25, fused
via RRF). Context assembled and sent to GPT-4o/Claude. Structured report output
validated by Pydantic. Each claim linked to source chunk.
7 Review Junior analyst reads report, posts disputed annotations. Disputed items block
approval. Senior analyst resolves disputes, edits findings, approves. Report locked.
8 Export & Email Approved report exported as formatted document. Q&A; list generated and emailed
to target company. Both actions logged to audit trail.
Page 14 Confidential

DealRoom AI — Capstone Project Proposal | 2026
06 AI Agent Design
Three specialist agents run in sequence for every analysis. All are built on LangGraph and fully traced in
LangSmith, tagged with deal_room_id and tenant_id for per-deal debugging and cost tracking.
6.1 Document Ingestion Agent
A sequential pipeline triggered by ARQ immediately after document upload. Not a ReAct loop — deterministic
steps in fixed order.
S Tool / Process Detail
t
e
p
1 PDF Parser (pdfplumber) Extracts prose text and tables separately. Tables are preserved as
structured row/column data, not fragmented text.
2 Section Classifier (LLM) Single gpt-4o-mini call classifies document as: financial_statement,
legal_contract, market_report, management_presentation, or other.
3 Hybrid Chunker Prose: RecursiveCharacterTextSplitter (512 tokens, 64 overlap). Tables:
each table is one atomic chunk serialised as structured text. All chunks
carry filename, page number, and section header metadata.
4 Embedding + Redis Cache get_embeddings_batch_cached() hashes each chunk, checks Redis
(7-day TTL), calls OpenAI only on misses. Batched in groups of 100.
5 pgvector Insert Bulk INSERT into document_chunks with tenant_id, deal_room_id, and
embedding vector. Default document_permissions granted to all deal
room members.
6.2 Research Agent
A LangGraph ReAct loop. The agent autonomously decides which tools to call, in what order, and when it has
gathered sufficient information. Results are cached in Redis for 24 hours per company per day.
Tool Data Source Returns
web_search Tavily / SerpAPI Recent news, press releases, analyst commentary
get_financial_data Yahoo Finance / Alpha Market cap, P/E, revenue, EBITDA margin,
Vantage debt-to-equity
get_news_sentiment NewsAPI + sentiment scoring 90-day sentiment score (-1 to 1), headline list
Page 15 Confidential

DealRoom AI — Capstone Project Proposal | 2026
Tool Data Source Returns
get_competitors Web search + LLM extraction Top 3-5 competitors with market share and notes
get_regulatory_filings SEC EDGAR full-text search Recent 10-K, 10-Q, 8-K with key excerpts
API
Loop control: Maximum 12 tool calls per run. The Evaluate node assesses whether all five research areas (news,
financials, competitive position, risk signals, regulatory) have sufficient evidence before allowing termination.
6.3 Synthesis Agent
Combines document knowledge (via RAG) and research findings to generate the structured report. A single
long-context LLM call with per-section targeted retrieval. Not a ReAct loop.
(cid:127) Retrieval: Each report section issues its own query against the pgvector store. Results from cosine similarity
search (top 15) and BM25 keyword search (top 15) are fused using Reciprocal Rank Fusion (k=60) and
re-ranked to a final top 5 per section.
(cid:127) Permission filter: The retrieval query joins through document_permissions before the ANN operator. The
synthesis agent never sees content the requesting user cannot access.
(cid:127) Output schema: Validated by Pydantic. Sections: executive_summary, financial_health, legal_flags,
commercial_assessment, red_flags, key_questions. Each item carries a citation to the source chunk (filename
+ page number).
(cid:127) Hallucination control: System prompt instructs the model to cite every factual claim. Automated
post-processing checks citation coverage — claims without citations are flagged in the report UI.
6.4 Supporting AI Calls (Lightweight)
Call Trigger What It Produces
Missing Context Generator After all documents Structured list of missing documents/data gaps
indexed linked to the report sections they would inform
Management Q&A; Generator User clicks Generate Priority-ranked questions grouped by category
Q&A; (financial, legal, operational, strategic), each
linked to source finding
Document Type Classifier Per document, during Single label from: financial_statement,
ingestion legal_contract, market_report,
management_presentation, other
Financial Ratio Extractor Before ML scoring Best-effort extraction of 8 financial ratios from
document chunks; null where not found
Page 16 Confidential

DealRoom AI — Capstone Project Proposal | 2026
07 RAG Pipeline & ML Risk Classifier
7.1 RAG Pipeline Architecture
Stage Component Detail
Ingestion pdfplumber + custom chunker Prose split at 512 tokens / 64 overlap. Tables preserved as
atomic chunks. Metadata: filename, page, doc_type,
section_header, deal_room_id, tenant_id.
Embedding text-embedding-3-small 1536-dimension OpenAI embeddings. Batched in groups of
100. Cached in Redis (7-day TTL) by SHA-256 hash of
chunk text.
Storage pgvector (PostgreSQL) HNSW index (m=16, ef_construction=64) for fast ANN.
Pre-filtered by tenant_id + deal_room_id +
document_permissions before ANN operator.
Retrieval Hybrid: cosine + BM25 + RRF Top-15 from pgvector cosine similarity. Top-15 from
rank_bm25 keyword search. Fused via Reciprocal Rank
Fusion. Re-ranked to top 5 per section.
Generation GPT-4o / Claude Sonnet Context: retrieved chunks + research findings + risk
assessment. System prompt mandates citations. Output:
Pydantic-validated JSON.
7.2 ML Financial Risk Classifier
A supervised classification model that scores the target company's financial health on four tiers. Provides a
reproducible, auditable quantitative signal that complements the qualitative synthesis agent output.
Features
Feature Formula Risk Signal
Current Ratio Current Assets / Current Below 1.0 indicates liquidity stress
Liabilities
Debt-to-Equity Total Debt / Shareholders High values indicate refinancing risk
Equity
Interest Coverage EBIT / Interest Expense Below 2.0 is a distress indicator
EBITDA Margin EBITDA / Revenue Negative = cash-burning business
Page 17 Confidential

DealRoom AI — Capstone Project Proposal | 2026
Feature Formula Risk Signal
Revenue Growth YoY (Rev_t - Rev_t-1) / Rev_t-1 Contraction signals demand risk
Cash Burn Rate Net Cash Flow / Cash Reserves Months of runway remaining
Working Capital Ratio Working Capital / Total Assets Operational buffer and efficiency
Gross Margin (Revenue - COGS) / Revenue Pricing power and cost structure
Model & Explainability
(cid:127) Algorithm: XGBoost gradient-boosted classifier within a scikit-learn Pipeline (SimpleImputer for nulls,
StandardScaler, XGBClassifier).
(cid:127) Training data: Public financial ratios from SEC EDGAR filings for S&P 1500 companies, labelled by
subsequent distress events within 24 months.
(cid:127) Evaluation: 5-fold stratified cross-validation. Gate: macro F1 >= 0.65 and no class F1 < 0.50. Blocks CI pipeline
on failure.
(cid:127) Explainability: SHAP TreeExplainer returns top 3 contributing features per prediction with direction
(increases/decreases risk) and magnitude.
(cid:127) Serving: Loaded at FastAPI startup. Inference cached in Redis indefinitely (invalidated on model redeploy). P95
latency target: <50ms.
Risk Tier Score Range Meaning
Low 0 – 33 No significant financial distress signals detected
Medium 34 – 55 One or more moderate concerns; warrants closer analysis
High 56 – 75 Multiple distress indicators; recommend expanded financial DD
Critical 76 – 100 Strong distress signals; may affect deal viability or price
Page 18 Confidential

DealRoom AI  —  Capstone Project Proposal  |  2026
08 Access Controls & Audit Trail
8.1 Three-Layer Access Control
DealRoom AI implements VDR-grade access controls with three independently enforced layers. Bypassing any
one layer does not grant access — all three must pass.
Layer 1 — Tenant Isolation
Every table carries a tenant_id column. All queries pass through BaseTenantRepository which automatically
appends the tenant filter. The application database user does not have cross-tenant visibility at any level.
Layer 2 — Deal Room Membership
A user in the tenant but not in deal_room_members for a specific deal room receives a 404 on any attempt to
access it — not a 403. They cannot infer the room exists. Roles within a deal room:
| Role           | View Report | Edit Items | Approve | Manage  | Grant Doc   |
| -------------- | ----------- | ---------- | ------- | ------- | ----------- |
|                |             |            | Report  | Members | Permissions |
| Owner          | Yes         | Yes        | Yes     | Yes     | Yes         |
| Senior Analyst | Yes         | Yes        | Yes     | No      | Yes         |
| Analyst        | Yes         | Yes        | No      | No      | No          |
| Viewer         | Yes         | No         | No      | No      | No          |
Approval gate: Before any approval request is processed, the API checks that (a) the caller has role 'owner'
or 'senior_analyst' in the deal room, AND (b) zero disputed annotations exist on the report. Both conditions
are checked atomically in a single transaction. Neither can be bypassed from the UI.
Layer 3 — Document-Level Permissions
Every document has an ACL in document_permissions. On upload, all four roles get can_view=True; owner and
senior_analyst also get can_download=True. Owners and senior analysts can restrict individual documents to
specific users or roles at any time. The pgvector retrieval query joins through this table before the ANN operator —
AI agents never surface content a user is not permitted to see.
8.2 Document Watermarking
Page 19 Confidential

DealRoom AI — Capstone Project Proposal | 2026
Every document download is watermarked before streaming to the client. The watermark is applied by pypdf and
includes the downloading user's full name, email address, and a UTC timestamp stamped diagonally across every
page. Raw file bytes from MinIO are never streamed directly. Watermarking acts as a deterrent against
unauthorised sharing and as a forensic tool in the event of a leak.
8.3 Audit Trail
The audit_log table is append-only. The application database user has INSERT and SELECT privileges only —
DELETE and UPDATE are revoked at the database level. Every state-changing action in the system writes an
audit entry in the same transaction as the action itself — both commit or neither does.
Audited Events
Category Events
Authentication user.login, user.login_failed, user.invited
Deal Rooms deal_room.created, deal_room.accessed, deal_room.archived
Permissions permission.member_invited, permission.member_removed, permission.role_changed,
permission.document_granted, permission.document_restricted
Documents document.uploaded, document.viewed, document.downloaded (with file size),
document.deleted
Reports report.analysis_started, report.item_edited, report.submitted_for_review,
report.approved, report.exported
Annotations annotation.created, annotation.resolved, annotation.disputed
Q&A; qa.generated, qa.email_sent (with recipient address)
Each entry stores: actor_id, actor_email (denormalised — survives user deletion), actor_role at time of action,
resource_type, resource_id, resource_name, action-specific metadata as JSONB, IP address, user agent, and a
nanosecond-precision timestamp. The activity log is accessible to owners and senior analysts via the deal room
UI, filterable by user, action type, and date range, and exportable as CSV.
Page 20 Confidential

DealRoom AI — Capstone Project Proposal | 2026
09 Redis: Task Queue & Caches
9.1 Task Queue (ARQ)
FastAPI BackgroundTasks runs jobs in the same process as the web server. If the server restarts during a
90-second ingestion or analysis job, the task is silently lost. ARQ (async Redis Queue) solves this: jobs are
enqueued in Redis, picked up by an independent worker process, and retried automatically on failure. The worker
runs as a separate Docker container and can be scaled horizontally.
Task Trigger Typical Duration Retry Policy
task_ingest_document Document upload 30 – 90 seconds 3 retries, 10s
backoff
task_run_analysis Analyst triggers analysis 60 – 120 seconds 3 retries, 10s
backoff
The API enqueues jobs and stores the ARQ job ID on the document or report row. The frontend polls GET
/api/jobs/{job_id}/status to show real-time progress (queued / in_progress / complete / failed) without blocking the
upload response.
9.2 Three Redis Caches
Cache Key Pattern TTL Expected Hit Rate
Embedding cache emb:{model}:{sha256(chunk_text 7 days 15-30% on real deals (boilerplate
)} clauses, standard templates)
Research cache research:{company}:{date} 24 hours High when multiple analysts run
analysis on same target same day
ML inference cache ml:risk:{sha256(ratios)} Indefinite 100% for repeated runs with
identical ratios; invalidated on
model redeploy
Embedding Cache Detail
Before calling OpenAI, each chunk text is hashed with SHA-256. The hash is looked up in Redis. On a hit, the
cached 1536-dimension vector is returned immediately. On a miss, OpenAI is called and the result is stored. This
works because the same 512-token clause (standard NDA boilerplate, audit sign-off language, company
registration text) appears across many documents from different deal rooms, often from different tenants. The
cache is model-scoped — if the embedding model changes, old keys are automatically ignored because the
model name is part of the key pattern.
Page 21 Confidential

DealRoom AI — Capstone Project Proposal | 2026
Research Cache Detail
Research results are date-scoped: the cache key includes today's date as an ISO string. This means results
expire naturally at midnight without requiring explicit TTL-based deletion. Multiple analysts running analysis on the
same target company on the same day share the cached research findings, avoiding redundant API calls and
ensuring consistency across concurrent runs on the same company.
Page 22 Confidential

DealRoom AI — Capstone Project Proposal | 2026
10 User Experience & Workflow
S Action What Happens
t
e
p
1 Register Firm registers. A tenant workspace is created. Team members are invited with
roles (Owner, Senior Analyst, Analyst, Viewer).
2 Dashboard All deal rooms visible in a risk heatmap: colour-coded cards showing risk tier,
document count, unresolved annotations, and current status.
3 Create Deal Room A named, isolated workspace is created for the target company. Only invited
members can access it.
4 Upload Documents PDFs and spreadsheets are uploaded. Files go to MinIO. ARQ worker indexes
them. Status badges update in real time via job polling.
5 Check Gaps Missing Context Generator identifies what is absent and lists what to request
from the client — before running analysis.
6 Run Analysis One click triggers the full pipeline: Research Agent, ML Scorer, Synthesis Agent.
A progress indicator tracks the ARQ job status.
7 Review Report Junior analyst reads the structured report. Each finding can be commented on,
verified, or disputed. Disputed items show as red badges.
8 Resolve & Approve Senior analyst resolves all disputes, makes final edits, and approves. Approval
is blocked until zero disputed annotations remain. Report locks on approval.
9 Export & Q&A; Approved report is exported. Q&A; list is generated from findings and sent via
email to the target company directly from the platform.
1 Compare Deals Any two deal rooms can be compared side by side: risk scores, financial ratios,
0 red flags, and key findings across active and historical deals.
1 Audit Log Owners and senior analysts can review the full chronological activity log for the
1 deal room — every access, edit, approval, and download with IP and timestamp.
Page 23 Confidential

DealRoom AI — Capstone Project Proposal | 2026
11 Two-Week Build Plan
Week 1 — Foundation, Access Controls & Core
Pipeline
Day Focus Key Deliverables
Day Scaffold + Auth + Infra Monorepo, Docker Compose (PostgreSQL + Redis + MinIO + backend
1 + worker + frontend), JWT auth, MinIO bucket init, ARQ worker process
running
Day Multi-tenancy + Membership deal_room_members table, DealRoomRepository with
2 membership-gated queries, member management endpoints, audit_log
table, log_event() helper, tenant isolation verified
Day Documents + MinIO + ARQ Documents upload to MinIO, ingestion pipeline via ARQ worker,
3 pgvector + HNSW index, document_permissions with default grants,
Redis embedding cache live
Day Research Agent + Cache LangGraph ReAct loop, all 5 research tools, Redis research cache,
4 LangSmith tracing tagged with deal_room_id
Day ML Classifier + Redis Cache XGBoost training, SHAP explainability, Redis inference cache,
5 /api/ml/risk-score endpoint, eval gate passes in CI
Week 2 — Synthesis, Review Workflow & Polish
Day Focus Key Deliverables
Day Synthesis + Full Pipeline Hybrid retrieval with permission filtering (cosine + BM25 + RRF),
6 Synthesis Agent with Pydantic output, full analysis pipeline via ARQ,
report items in DB with citations
Day Report UI + Approval Three-panel report viewer, RiskScoreCard with SHAP bars,
7 ApprovalBar, approval workflow with dispute-gate enforcement (409 on
unresolved disputes), report locking
Day Annotations + Permissions Annotation threading, disputed annotation badges, document
8 + Watermark permission management, pypdf watermarking on download, all audit
events firing
Day Q&A; + Email + Audit Log UI Q&A; generation and email dispatch, AuditLog.jsx activity feed with
9 + CI filters, GitHub Actions CI with backend tests + ML eval + prompt
regression
Page 24 Confidential

DealRoom AI — Capstone Project Proposal | 2026
Day Focus Key Deliverables
Day Deal Comparison + Polish Side-by-side deal comparison, end-to-end run on two real public
10 company PDFs, empty states, loading skeletons, README, demo
script rehearsal
Demo-ready definition: Register to dashboard in 30s. Upload to indexed in 90s. Analysis to full cited report
in 120s. Risk score with SHAP renders. Disputed annotation blocks approval (409 visible). Approval locks
report. Download shows watermark. Audit log shows 8+ event types. Two tenant accounts cannot see each
other's data.
Page 25 Confidential

DealRoom AI — Capstone Project Proposal | 2026
12 Strategic Positioning for Big 4
The four major professional services firms — Deloitte, PwC, EY, and KPMG — collectively conduct hundreds of
buy-side and sell-side due diligence engagements per year. DealRoom AI is positioned as a force-multiplier for
their transactions and advisory practices, not a replacement for senior judgment.
12.1 Alignment to Practice Areas
Practice Area How DealRoom AI Maps
Transactions / Deals Financial DD acceleration is the primary use case — directly addresses the
highest-cost, most time-constrained part of any M&A; engagement
Risk Advisory ML risk scoring with SHAP explainability and the document-level ACL model map
directly to risk assessment and data governance service lines
Technology Consulting Multi-agent architecture, LangGraph, LangSmith, and pgvector demonstrate
applied AI-at-scale thinking that resonates with tech practice leads
Data & AI The full production stack — ARQ queues, Redis caches, pgvector, XGBoost +
SHAP, LangSmith observability — is the current enterprise AI engineering toolkit
12.2 Technical Signals That Stand Out
(cid:127) VDR-grade access controls — three-layer isolation (tenant, membership, document ACL) directly answers the
data governance question every partner asks about AI tools handling sensitive client data.
(cid:127) Append-only audit trail with DB-level REVOKE — shows awareness of compliance requirements, not just
application-layer security theatre.
(cid:127) Document-permission-filtered RAG — the retrieval query joins through the ACL before the ANN operator
runs. This is a subtle but important signal that security was considered at the architecture level, not bolted on
afterward.
(cid:127) ARQ queue over BackgroundTasks — shows understanding of production reliability concerns: tasks survive
server restarts, failures retry automatically, workers scale independently.
(cid:127) SHAP explainability on ML outputs — directly addresses the 'black box' objection clients raise about
AI-generated risk assessments.
(cid:127) LangSmith observability with cost tracking — shows production thinking. A partner's first question is often
'what does this cost per deal?' — this answers it.
(cid:127) Approval workflow with dispute gate — a named human signs off on every report before it leaves the
platform. This is the governance control that makes AI-assisted DD acceptable in a regulated professional
services context.
Page 26 Confidential

DealRoom AI — Capstone Project Proposal | 2026
DealRoom AI is not a toy demo. It is a scoped but production-honest system that addresses a real,
expensive, and widely understood problem — and demonstrates the engineering maturity to make it
trustworthy. That is the combination that opens conversations in a Big 4 technical interview.
DealRoom AI — Capstone Project Proposal — AI Engineering Bootcamp 2026 — SE Factory, Beirut Digital District
Page 27 Confidential