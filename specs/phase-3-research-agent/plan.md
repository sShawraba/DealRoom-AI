# Phase 3 — Research Agent
## plan.md

### New Files
```
backend/app/agents/research/
  agent.py     build_research_graph(), run_research_agent_cached()
  tools.py     all 5 @tool functions
```

### LangGraph State
```python
class ResearchState(TypedDict):
    target_company: str
    deal_room_id: str
    tenant_id: str
    messages: Annotated[list, add_messages]
    research_findings: dict
    tool_call_count: int
    sufficient: bool
```

### Graph
```python
graph = StateGraph(ResearchState)
graph.add_node("reason", reason_node)    # LLM + tool binding
graph.add_node("act", act_node)          # ToolNode execution
graph.add_node("evaluate", evaluate_node)
graph.set_entry_point("reason")
graph.add_edge("reason", "act")
graph.add_edge("act", "evaluate")
graph.add_conditional_edges("evaluate", should_continue, {"reason": "reason", END: END})
```
`should_continue`: returns END if `sufficient or tool_call_count >= 12`

### System Prompt
```
You are a senior M&A research analyst. Research the target company across:
1. Recent news (last 90 days)   2. Key financial metrics
3. Competitive landscape         4. Risk signals
5. Regulatory filings (if public)
Use each tool at most once per query. Stop when all 5 areas have findings.
Set sufficient=True when done.
```

### Redis Cache Function
```python
async def run_research_agent_cached(target_company, deal_room_id, tenant_id):
    redis = await get_redis()
    normalised = target_company.lower().strip().replace(" ", "_")
    key = f"research:{normalised}:{date.today().isoformat()}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    graph = build_research_graph()
    result = await graph.ainvoke(initial_state, config=langsmith_config)
    findings = result["research_findings"]
    await redis.setex(key, settings.RESEARCH_CACHE_TTL, json.dumps(findings))
    return findings
```

### Tool Stubs (use if API keys unavailable)
Each tool returns hardcoded JSON for 3 known companies (Apple, Microsoft, Tesla). Real implementations use Tavily, yfinance, NewsAPI. Stub vs real controlled by env var `USE_RESEARCH_STUBS=true`.

---
---

## Agent Improvements

### Parallel Tool Execution
After `web_search` establishes company context, three tools run in parallel:

```python
# In the LangGraph act_node, detect when we have company context
# and can parallelise independent tools

async def parallel_research(company_name: str, context: str) -> dict:
    """
    web_search runs first to establish context.
    Then financial + news + regulatory run concurrently.
    get_competitors runs last (may use industry from web_search).
    """
    financial_task   = get_financial_data(company_name)
    news_task        = get_news_sentiment(company_name)
    regulatory_task  = get_regulatory_filings(company_name)

    financial, news, regulatory = await asyncio.gather(
        financial_task, news_task, regulatory_task
    )
    competitors = await get_competitors(company_name,
                                        industry=context.get("industry"))
    return {
        "financial":   financial,
        "news":        news,
        "regulatory":  regulatory,
        "competitors": competitors,
    }
```

### Tool Result Size Limits
Every tool truncates output to 2000 tokens before returning to the LLM. A single SEC filing could fill the entire context window otherwise.

```python
MAX_TOOL_OUTPUT_TOKENS = 2000

def truncate_tool_output(output: str) -> str:
    # Rough token estimate: 4 chars per token
    max_chars = MAX_TOOL_OUTPUT_TOKENS * 4
    if len(output) > max_chars:
        return output[:max_chars] + "\n... [truncated]"
    return output
```

### Pydantic Tool Output Models
Every tool returns a typed Pydantic model, not a raw JSON string. `ToolError` is returned on failure.

```python
class WebSearchResult(BaseModel):
    results: list[SearchResult]
    source: str = "web"

class FinancialSnapshot(BaseModel):
    market_cap: str | None
    revenue_ttm: str | None
    ebitda_margin: str | None
    debt_to_equity: str | None
    revenue_growth_yoy: str | None
    source: str

class ToolError(BaseModel):
    error: str
    retryable: bool
    tool_name: str
```

### Within-Run Tool Deduplication
Cache tool calls within a single agent run using a simple dict:

```python
class ResearchState(TypedDict):
    ...
    tool_call_cache: dict  # {"tool_name:arg_hash": result} — prevents duplicate API calls
```

Before executing a tool, check `tool_call_cache`. If hit, return cached result directly.

### Progress Events
The research agent publishes streaming events:

```python
# At the start of research:
await publish_progress(report_id, AnalysisEvent.RESEARCH_START)

# After web_search completes:
await publish_progress(report_id, "research.web_complete",
                       company=target_company)

# After parallel tools complete:
await publish_progress(report_id, "research.data_complete")
```

### Stub Mode
All tools check `settings.USE_RESEARCH_STUBS`. When True, return hardcoded fixtures for 3 known companies (Apple, Microsoft, Tesla). Used in CI tests to avoid real API calls.