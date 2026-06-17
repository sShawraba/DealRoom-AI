# DealRoom AI — Agent Specifications

## Overview

Three agents run in sequence as part of `run_full_analysis`. All are built with LangGraph and traced via LangSmith. Tag every run with `{"deal_room_id": str, "tenant_id": str}` metadata.

```
Document Ingestion Agent   (runs on upload, async background)
         ↓
Research Agent             (runs on analysis trigger)
         ↓
Synthesis Agent            (runs after research, produces report)
```

---

## Agent 1: Document Ingestion Agent

**Location:** `app/agents/ingestion/`
**Trigger:** FastAPI BackgroundTask on document upload
**Purpose:** Parse, chunk, embed, and store all uploaded documents into pgvector

### Pipeline (not a ReAct loop — sequential pipeline)

```python
# agents/ingestion/agent.py

async def run_ingestion(document_id: UUID, session: AsyncSession):
    """
    Sequential pipeline — not a ReAct loop.
    Each step passes its output to the next.
    """
    # Step 1: Load file from disk
    # Step 2: Parse with appropriate tool based on file type
    # Step 3: Classify document type
    # Step 4: Chunk content
    # Step 5: Embed chunks in batches
    # Step 6: Write to document_chunks table
```

### Tool: PDF Parser

```python
# agents/ingestion/tools.py

def parse_pdf(file_path: str) -> dict:
    """
    Uses pdfplumber.
    Returns:
    {
      "pages": [
        {
          "page_number": int,
          "text_blocks": [str],          # prose paragraphs
          "tables": [                    # each table as list-of-rows
            {
              "headers": [str],
              "rows": [[str]],
              "page_number": int,
              "caption": str | None
            }
          ]
        }
      ],
      "total_pages": int
    }
    - Tables are extracted separately from prose.
    - Empty pages are skipped.
    - Runs of whitespace are normalised.
    """
```

### Tool: Section Classifier

```python
def classify_document_type(filename: str, first_500_chars: str) -> doc_type:
    """
    Single lightweight LLM call (gpt-4o-mini).
    System prompt:
      "Classify this document as one of:
       financial_statement | legal_contract | market_report |
       management_presentation | other
       Reply with ONLY the classification label."
    Returns: one of the doc_type enum values
    """
```

### Chunker

```python
# agents/ingestion/chunker.py

CHUNK_SIZE = 512      # tokens
CHUNK_OVERLAP = 64    # tokens

def chunk_document(parsed: dict, document_id: UUID, deal_room_id: UUID, tenant_id: UUID) -> list[dict]:
    """
    Returns a list of chunk dicts ready for DB insertion.

    Rules:
    - Prose blocks: use RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)
    - Tables: each table is ONE chunk regardless of size, serialised as:
        "TABLE: {caption}\nHeaders: col1 | col2 | col3\nRow 1: val | val | val\n..."
    - Each chunk carries metadata:
        content_type: 'prose' | 'table'
        page_number: int
        section_header: nearest heading above this chunk (or None)
        chunk_index: sequential int within this document

    Returns: [
      {
        "content": str,
        "content_type": str,
        "page_number": int,
        "section_header": str | None,
        "chunk_index": int,
        "token_count": int
      }
    ]
    """
```

### Embedding Batch Insert

```python
async def embed_and_store_chunks(chunks: list[dict], document_id: UUID, deal_room_id: UUID, tenant_id: UUID, session: AsyncSession):
    """
    - Embed in batches of 100 using openai.embeddings.create(model="text-embedding-3-small")
    - Insert all chunks in a single bulk INSERT into document_chunks
    - Use asyncpg's executemany for performance
    """
```

---

## Agent 2: Research Agent

**Location:** `app/agents/research/`
**Pattern:** LangGraph ReAct loop
**Purpose:** Autonomously research the target company using external tools. Enrich the deal room with public data not available in uploaded documents.

### LangGraph State

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class ResearchState(TypedDict):
    target_company: str
    deal_room_id: str
    tenant_id: str
    messages: Annotated[list, add_messages]
    research_findings: dict        # accumulated structured findings
    tool_call_count: int           # stop at MAX_TOOL_CALLS
    sufficient: bool               # set to True by evaluate node to stop loop
```

### Graph Definition

```python
from langgraph.graph import StateGraph, END

def build_research_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("reason", reason_node)       # LLM decides what to do next
    graph.add_node("act", act_node)             # Executes one tool call
    graph.add_node("evaluate", evaluate_node)   # Decides if we have enough

    graph.set_entry_point("reason")
    graph.add_edge("reason", "act")
    graph.add_edge("act", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        should_continue,           # returns "reason" or END
        {"reason": "reason", END: END}
    )

    return graph.compile()

MAX_TOOL_CALLS = 12

def should_continue(state: ResearchState) -> str:
    if state["sufficient"] or state["tool_call_count"] >= MAX_TOOL_CALLS:
        return END
    return "reason"
```

### System Prompt

```
You are a senior M&A research analyst. Your job is to research a target company
using available tools and build a comprehensive intelligence picture.

You are looking for:
1. Recent news (positive or negative) about the company
2. Key financial metrics and market position
3. Competitive landscape and market share
4. Any regulatory, legal, or reputational risks
5. Management changes, departures, or controversies

Be specific and cite the source of each finding.
When you have sufficient information across all 5 areas, set sufficient=True.
Do not call a tool more than once with the same query.
```

### Tools

```python
# agents/research/tools.py

@tool
def web_search(query: str) -> str:
    """Search the web for information about the target company.
    Use specific queries. Prefer recent results (add current year to query).
    Returns: list of { title, url, snippet } as JSON string."""
    # Implementation: use SerpAPI or Tavily API

@tool
def get_financial_data(ticker_or_company: str) -> str:
    """Get key financial ratios and metrics for a company.
    Works best with stock ticker symbols.
    Returns: { market_cap, pe_ratio, revenue_ttm, ebitda_margin,
               debt_to_equity, current_ratio, revenue_growth_yoy } as JSON string.
    Returns null fields if company is private or data unavailable."""
    # Implementation: yfinance or Alpha Vantage

@tool
def get_news_sentiment(company_name: str, days_back: int = 90) -> str:
    """Get recent news headlines and sentiment score for a company.
    Returns: { overall_sentiment: float (-1 to 1),
               headline_count: int,
               headlines: [{ title, date, sentiment, url }] } as JSON string."""
    # Implementation: NewsAPI + simple sentiment scoring

@tool
def get_competitors(company_name: str, industry: str = None) -> str:
    """Identify top competitors for a company.
    Returns: [{ name, estimated_market_share, notes }] as JSON string."""
    # Implementation: web search with structured extraction via LLM

@tool
def search_regulatory_filings(company_name: str) -> str:
    """Search SEC EDGAR for recent filings (10-K, 10-Q, 8-K).
    Returns null if company is not publicly listed.
    Returns: [{ form_type, date, url, key_excerpt }] as JSON string."""
    # Implementation: SEC EDGAR full-text search API
```

### Output Schema (research_findings)

```python
{
  "company_overview": str,                    # 2-3 sentence summary
  "recent_news": [
    { "headline": str, "date": str, "sentiment": str, "source": str }
  ],
  "financial_snapshot": {
    "market_cap": str | None,
    "revenue_ttm": str | None,
    "ebitda_margin": str | None,
    "debt_to_equity": str | None,
    "revenue_growth_yoy": str | None,
    "source": str
  },
  "competitive_position": str,
  "competitors": [{ "name": str, "notes": str }],
  "risk_signals": [str],                      # list of flagged concerns
  "sources_consulted": [str]                  # URLs or descriptions
}
```

---

## Agent 3: Synthesis Agent

**Location:** `app/agents/synthesis/`
**Pattern:** RAG retrieval + structured LLM generation (NOT a ReAct loop)
**Purpose:** Combine document knowledge (via RAG) and research findings to generate the structured DD report

### Retriever

```python
# agents/synthesis/retriever.py

async def hybrid_retrieve(
    query: str,
    deal_room_id: UUID,
    tenant_id: UUID,
    session: AsyncSession,
    top_k: int = 15,
    content_types: list[str] | None = None
) -> list[dict]:
    """
    Hybrid retrieval combining semantic search + BM25 keyword search.

    Step 1: Semantic search via pgvector (top 15)
      - Embed query with text-embedding-3-small
      - Run pgvector cosine similarity query (see database spec)

    Step 2: BM25 keyword search (top 15)
      - Use pg_trgm similarity or in-memory BM25 (rank_bm25 library)
      - Run against document_chunks.content for tenant+deal_room

    Step 3: Reciprocal Rank Fusion (RRF)
      - Merge two ranked lists using RRF formula: score = 1 / (k + rank)
      - k = 60 (standard RRF constant)
      - Deduplicate by chunk id
      - Return top_k by fused score

    Returns: [
      {
        "chunk_id": str,
        "content": str,
        "filename": str,
        "page_number": int,
        "doc_type": str,
        "similarity": float,
        "content_type": str
      }
    ]
    """
```

### Section Queries

```python
# Each section gets its own targeted retrieval query
SECTION_QUERIES = {
    "executive_summary":     "company overview business model revenue operations",
    "financial_health":      "revenue profit EBITDA margin debt cash flow working capital balance sheet",
    "legal_flags":           "contracts litigation IP indemnity change of control warranties representations",
    "commercial_assessment": "market share customers competitors pricing growth strategy",
    "red_flags":             "risks liabilities contingencies disputes defaults penalties write-offs",
    "key_questions":         "anomalies inconsistencies gaps management projections assumptions"
}
```

### System Prompt (Synthesis)

```
You are a senior M&A due diligence analyst at a Big 4 consulting firm.

You will be given:
1. Excerpts retrieved from the target company's uploaded documents
2. Research findings from external sources
3. A financial risk score and the top contributing factors

Your task is to produce a structured due diligence brief.

RULES:
- Every factual claim MUST include a citation in this exact format: [SOURCE: filename.pdf, p.12]
- If you cannot cite a claim from the provided excerpts, do not make it
- Flag uncertainty explicitly: "Based on available documents, however..."
- Be specific — name figures, dates, clauses
- Do not pad. Each item should be 1-3 sentences maximum.
- Return ONLY valid JSON matching the output schema. No preamble.
```

### Output Schema (Pydantic)

```python
from pydantic import BaseModel
from typing import List, Optional

class ReportItemRaw(BaseModel):
    content: str                        # finding text with inline citations
    citation: Optional[dict] = None     # { filename, page, chunk_id }

class ReportSectionRaw(BaseModel):
    items: List[ReportItemRaw]

class SynthesisOutput(BaseModel):
    executive_summary:     ReportSectionRaw
    financial_health:      ReportSectionRaw
    legal_flags:           ReportSectionRaw
    commercial_assessment: ReportSectionRaw
    red_flags:             ReportSectionRaw
    key_questions:         ReportSectionRaw
```

### Synthesis Runner

```python
# agents/synthesis/agent.py

async def run_synthesis(
    report_id: UUID,
    deal_room_id: UUID,
    tenant_id: UUID,
    research_findings: dict,
    risk_assessment: RiskScoreResponse,
    session: AsyncSession
) -> SynthesisOutput:
    """
    1. For each section in SECTION_QUERIES, run hybrid_retrieve
    2. Deduplicate retrieved chunks across sections
    3. Build context string:
         - Retrieved document excerpts (labelled by source)
         - Research findings summary
         - Risk score and SHAP factors
    4. Single LLM call with full context + system prompt
    5. Parse response as SynthesisOutput (Pydantic)
    6. For each item, resolve citation back to chunk_id in retrieved set
    7. Return SynthesisOutput

    Token budget: keep context under 100k tokens for gpt-4o
    If exceeded: prioritise higher-similarity chunks, truncate lower ones
    """
```

---

## Management Q&A Generator

**Not a LangGraph agent — a single focused LLM call.**

```python
# services/report_service.py

async def generate_management_qa(report_id: UUID, session: AsyncSession) -> list[dict]:
    """
    1. Fetch all report_items for this report (red_flags + financial_health + legal_flags)
    2. Build prompt with all findings
    3. Single gpt-4o call with structured output
    4. Parse and store in management_questions table
    """

SYSTEM_PROMPT_QA = """
You are a senior M&A advisor preparing for a formal management Q&A session.

Given the due diligence findings below, generate sharp, specific questions for target management.

Rules:
- Each question must be directly traceable to a specific finding (include source_item_index)
- Group by category: financial | legal | operational | strategic
- Priority: critical (material deal risk) | high (significant concern) | medium (clarification needed)
- Questions should be precise enough that a vague answer is itself a red flag
- Do not generate generic questions — every question must address something specific found

Return ONLY valid JSON: { "categories": [{ "name": str, "questions": [{ "question": str, "priority": str, "source_item_index": int }] }] }
"""
```

---

## LangSmith Tracing Setup

```python
# Add to every agent run

from langsmith import Client
from langchain.callbacks import LangChainTracer

tracer = LangChainTracer(
    project_name=settings.LANGCHAIN_PROJECT,
    tags=["dealroom-ai"]
)

# Pass to every LLM call and graph invocation:
config = {
    "callbacks": [tracer],
    "metadata": {
        "deal_room_id": str(deal_room_id),
        "tenant_id": str(tenant_id),
        "report_id": str(report_id)
    }
}

# Invoke graph:
result = graph.invoke(initial_state, config=config)
```

---

## Cost & Token Tracking

```python
# After each agent run, update the report row

total_tokens = sum(
    cb.total_tokens
    for cb in callbacks
    if hasattr(cb, 'total_tokens')
)

# Rough cost estimate (update rates as needed)
COST_PER_1K_TOKENS = {
    "gpt-4o": 0.005,         # per 1k output tokens
    "gpt-4o-mini": 0.0006,
    "text-embedding-3-small": 0.00002
}
```
