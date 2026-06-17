# Phase 3 — Research Agent
## tasks.md

- [ ] **Task 01** — Write `app/agents/research/tools.py`: `web_search(query)`, `get_financial_data(ticker_or_company)`, `get_news_sentiment(company_name, days_back=90)`, `get_competitors(company_name)`, `get_regulatory_filings(company_name)` — all decorated with `@tool`, all return JSON strings, all handle exceptions gracefully (return `{"error": str(e)}`)
- [ ] **Task 02** — Add stub mode to each tool: if `settings.USE_RESEARCH_STUBS=true` return hardcoded fixture JSON. Add `USE_RESEARCH_STUBS: bool = False` to config.py
- [ ] **Task 03 [needs 01]** — Write `app/agents/research/agent.py`: `ResearchState` TypedDict, `reason_node`, `act_node` (ToolNode with all 5 tools), `evaluate_node`, `should_continue`, `build_research_graph()`
- [ ] **Task 04 [needs 03]** — Implement `run_research_agent_cached(target_company, deal_room_id, tenant_id)` with Redis cache check before graph invocation
- [ ] **Task 05 [needs 04]** — Add LangSmith config: pass `{"callbacks": [tracer], "metadata": {"deal_room_id": ..., "tenant_id": ...}}` to `graph.ainvoke()`
- [ ] **Task 06 [needs 03]** — Add `if __name__ == "__main__"` block to `agent.py` for standalone testing: `asyncio.run(run_research_agent_cached(sys.argv[1], "test", "test"))` then print findings
- [ ] **Task 07 [needs 04,05]** — Write `tests/test_research_agent.py`: run agent with stub mode on known company, verify all 6 keys in output, verify Redis cache set, run again and verify cache hit (no tool calls), verify tool_call_count <= 12
- [ ] **Task 08 [needs 07]** — Run `pytest tests/test_research_agent.py -v` — all pass

- [ ] **Task 09 (parallel tools)** — In the `act_node`, identify which tool calls are independent and run them with `asyncio.gather()` where possible. Specifically: `get_news_sentiment` and `get_financial_data` and `get_regulatory_filings` can all run in parallel when the company name is the only input. Only `get_competitors` (which depends on knowing the industry) should run sequentially after web_search.
- [ ] **Task 10 (cache invalidation)** — Add `invalidate_research_cache(company_name: str)` function:
    ```python
    async def invalidate_research_cache(company_name: str):
        redis = await get_redis()
        normalised = company_name.lower().strip().replace(" ", "_")
        # Delete all date-variants: research:{name}:* 
        keys = await redis.keys(f"research:{normalised}:*")
        if keys: await redis.delete(*keys)
    ```
    Expose via `DELETE /api/v1/admin/cache/research/{company_name}` in admin router.

## Agent Improvement Tasks
- [ ] **Task 09 (parallel execution)** — Refactor the research agent's act_node: run `get_financial_data`, `get_news_sentiment`, and `get_regulatory_filings` concurrently via `asyncio.gather()` after `web_search` establishes company context. `get_competitors` runs last using industry from web_search result.
- [ ] **Task 10 (size limits)** — Add `truncate_tool_output(output: str, max_tokens: int = 2000) -> str` to `app/agents/research/tools.py`. Apply to every tool's return value before returning.
- [ ] **Task 11 (Pydantic outputs)** — Define `WebSearchResult`, `FinancialSnapshot`, `NewsSentimentResult`, `CompetitorsList`, `RegulatoryFilings`, `ToolError` Pydantic models in `app/agents/research/tools.py`. All tools return these types, never raw dicts. On exception: return `ToolError(error=str(e), retryable=is_retryable(e), tool_name="...")`.
- [ ] **Task 12 (deduplication)** — Add `tool_call_cache: dict` to `ResearchState`. In act_node: hash `tool_name + args`, check cache before executing, store result after. Log cache hits to structlog.
- [ ] **Task 13 (streaming events)** — Import `publish_progress` and `AnalysisEvent` from `app/services/streaming`. Publish `RESEARCH_START` before the graph runs, `RESEARCH_DONE` after with `company_overview` field.
- [ ] **Task 14 (tests update)** — Add to `tests/test_research_agent.py`: `test_parallel_tools_faster_than_sequential`, `test_tool_output_truncated_at_limit`, `test_tool_error_returned_not_raised`, `test_deduplication_prevents_duplicate_calls`