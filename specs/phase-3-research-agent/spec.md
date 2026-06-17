# Phase 3 — Research Agent
## spec.md

### Overview
Build the Research Agent: a LangGraph ReAct loop that autonomously investigates a target company using five external tools. Results are cached in Redis for 24 hours per company per day. Every run is fully traced in LangSmith. The agent is invoked as part of the full analysis pipeline in Phase 5 — this phase builds and tests it in isolation.

### User Stories
- As the system, I invoke the research agent with a company name and receive structured findings covering news, financials, competitive position, risk signals, and regulatory data.
- As a developer, I see the full trace of every tool call in LangSmith tagged with deal_room_id.
- As the system, running the agent twice for the same company on the same day returns the cached result — no tool calls on the second run.

### Requirements
- LangGraph `StateGraph`: nodes `reason` (LLM picks next action), `act` (executes tool), `evaluate` (LLM checks if sufficient)
- State fields: `target_company`, `deal_room_id`, `tenant_id`, `messages`, `research_findings: dict`, `tool_call_count: int`, `sufficient: bool`
- Max 12 tool calls. Stop when `sufficient=True` OR `tool_call_count >= 12`
- Five tools: `web_search` (Tavily), `get_financial_data` (yfinance), `get_news_sentiment` (NewsAPI + scoring -1 to 1), `get_competitors` (web search + LLM extraction), `get_regulatory_filings` (SEC EDGAR API — returns null gracefully for private companies)
- Redis cache: key `research:{company_normalised}:{YYYY-MM-DD}`, TTL `RESEARCH_CACHE_TTL` (default 86400s)
- LangSmith: tag runs with `{"deal_room_id": str, "tenant_id": str}`
- Output dict keys: `company_overview`, `recent_news: list`, `financial_snapshot: dict`, `competitive_position: str`, `competitors: list`, `risk_signals: list`, `sources_consulted: list`

### Acceptance Criteria
```bash
python -m app.agents.research.agent "Apple Inc"
# → prints research_findings JSON with all 6 keys populated
# LangSmith project shows trace with tool calls visible
# Run twice same company same day → second call hits Redis (redis-cli keys "research:apple_inc:*" shows key)
# tool_call_count in returned state <= 12
```
