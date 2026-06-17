# Phase 3 — Research Agent: Implementation Summary

## Files Created / Modified

| File | Action | Description |
|------|--------|-------------|
| `backend/app/agents/research/__init__.py` | Created | Package init |
| `backend/app/agents/research/tools.py` | Created | 5 research tools with Pydantic models, stubs, truncation |
| `backend/app/agents/research/agent.py` | Created | LangGraph ReAct loop, caching, dedup, parallel exec |
| `backend/app/services/streaming.py` | Created | Streaming event stub (AnalysisEvent, publish_progress) |
| `backend/app/core/config.py` | Modified | Added `USE_RESEARCH_STUBS: bool = False` |
| `backend/app/routers/admin.py` | Modified | Added `DELETE /api/v1/admin/cache/research/{company_name}` |
| `backend/tests/conftest.py` | Modified | ForwardRef._evaluate Python 3.12 compat patch |
| `backend/tests/test_research_agent.py` | Created | 8 tests — all pass |

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `run_research_agent_cached("Apple Inc", ...)` returns dict with all 7 keys | ✅ |
| Redis cache set on first run (`research:apple_inc:YYYY-MM-DD`) | ✅ |
| Second call returns cached result, no LLM invoked | ✅ |
| `tool_call_count <= 12` | ✅ |
| Parallel tools (`get_financial_data`, `get_news_sentiment`, `get_regulatory_filings`) faster than sequential | ✅ |
| Tool output truncated at 8000 chars with `... [truncated]` marker | ✅ |
| Tool exceptions return `ToolError` JSON, never re-raise | ✅ |
| Within-run deduplication: 2 identical calls → 1 real execution | ✅ |
| `DELETE /api/v1/admin/cache/research/{company_name}` invalidates keys | ✅ |
| All 26 existing tests still pass | ✅ |

## Architecture Notes

- **Graph**: `reason → act → evaluate` with conditional edges; `reason` skips `act` if LLM returns no tool calls
- **Parallel execution**: `web_search`, `get_competitors` run sequentially; `get_financial_data`, `get_news_sentiment`, `get_regulatory_filings` run concurrently via `asyncio.gather()`
- **Deduplication**: within-run `tool_call_cache` dict in `ResearchState` keyed by `sha256(tool_name + args)[:16]`; detects both cross-run and same-batch duplicates
- **Python 3.12 compat fix**: `langsmith==0.1.57` + pydantic v1 compat layer crashes on Python 3.12 due to `ForwardRef._evaluate` signature change; patched in `conftest.py` by adding `recursive_guard=frozenset()` default

## Output Keys

```
company_overview, recent_news, financial_snapshot,
competitive_position, competitors, risk_signals, sources_consulted
```
