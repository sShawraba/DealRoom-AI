"""
Tests for the Phase 3 Research Agent.

Uses USE_RESEARCH_STUBS=True for all tool calls.
Mocks ChatOpenAI and Redis to avoid external dependencies.
"""
from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, ToolMessage

# ── Fixtures & helpers ─────────────────────────────────────────────────────────

EXPECTED_KEYS = {
    "company_overview",
    "recent_news",
    "financial_snapshot",
    "competitive_position",
    "competitors",
    "risk_signals",
    "sources_consulted",
}

_STUB_FINDINGS = {
    "company_overview": "Apple Inc. is a technology company known for iPhone and Mac.",
    "recent_news": [{"title": "Apple Q4 results beat estimates", "sentiment": 0.8}],
    "financial_snapshot": {"market_cap": "$2.8T", "revenue_ttm": "$385B"},
    "competitive_position": "Market leader in smartphones and wearables.",
    "competitors": ["Samsung", "Google", "Microsoft"],
    "risk_signals": ["regulatory scrutiny", "supply chain concentration"],
    "sources_consulted": ["web_search", "get_financial_data", "get_news_sentiment",
                          "get_competitors", "get_regulatory_filings"],
}


def _make_redis_mock(cached_value: bytes | None = None) -> MagicMock:
    """Return an async-capable Redis mock."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=cached_value)
    mock.setex = AsyncMock()
    mock.keys = AsyncMock(return_value=[])
    mock.delete = AsyncMock()
    return mock


def _make_llm_mock() -> MagicMock:
    """
    Mock ChatOpenAI with two behaviours:
    - First ainvoke (reason_node): returns AIMessage with 5 tool calls.
    - Subsequent ainvoke (evaluate_node): returns sufficient=True with full findings.
    """
    call_count = 0

    reason_msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "web_search",            "args": {"query": "Apple Inc M&A research"},         "id": "c1", "type": "tool_call"},
            {"name": "get_financial_data",     "args": {"ticker_or_company": "Apple"},              "id": "c2", "type": "tool_call"},
            {"name": "get_news_sentiment",     "args": {"company_name": "Apple Inc"},               "id": "c3", "type": "tool_call"},
            {"name": "get_competitors",        "args": {"company_name": "Apple Inc"},               "id": "c4", "type": "tool_call"},
            {"name": "get_regulatory_filings", "args": {"company_name": "Apple Inc"},               "id": "c5", "type": "tool_call"},
        ],
    )
    evaluate_msg = AIMessage(content=json.dumps({
        "sufficient": True,
        "findings_summary": _STUB_FINDINGS,
    }))

    async def _ainvoke(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        # Identify evaluate_node by its system prompt keyword
        sys_content = messages[0].content if messages else ""
        if "evaluating research completeness" in sys_content:
            return evaluate_msg
        return reason_msg

    class _MockBound:
        async def ainvoke(self, msgs, **kw):
            return await _ainvoke(msgs, **kw)

    class _MockLLM:
        def __init__(self, *a, **kw):
            pass

        def bind_tools(self, tools):
            return _MockBound()

        async def ainvoke(self, msgs, **kw):
            return await _ainvoke(msgs, **kw)

    return _MockLLM


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_research_agent_stub_returns_all_keys():
    """With stubs and mocked LLM, run_research_agent_cached returns all 7 required keys."""
    from app.core.config import settings
    from app.agents.research.agent import run_research_agent_cached

    redis_mock = _make_redis_mock(cached_value=None)
    MockLLM = _make_llm_mock()

    with patch.object(settings, "USE_RESEARCH_STUBS", True), \
         patch("app.agents.research.agent.get_redis", AsyncMock(return_value=redis_mock)), \
         patch("app.agents.research.agent.ChatOpenAI", MockLLM):

        findings = await run_research_agent_cached("Apple Inc", "deal-001", "tenant-001")

    assert isinstance(findings, dict), "findings must be a dict"
    missing = EXPECTED_KEYS - set(findings.keys())
    assert not missing, f"Missing keys in findings: {missing}"


@pytest.mark.asyncio
async def test_redis_cache_set_after_first_run():
    """After the first run, Redis.setex is called with the correct key prefix."""
    from app.core.config import settings
    from app.agents.research.agent import run_research_agent_cached

    redis_mock = _make_redis_mock(cached_value=None)
    MockLLM = _make_llm_mock()

    with patch.object(settings, "USE_RESEARCH_STUBS", True), \
         patch("app.agents.research.agent.get_redis", AsyncMock(return_value=redis_mock)), \
         patch("app.agents.research.agent.ChatOpenAI", MockLLM):

        await run_research_agent_cached("Apple Inc", "deal-001", "tenant-001")

    redis_mock.setex.assert_called_once()
    call_args = redis_mock.setex.call_args
    key = call_args[0][0]
    assert key.startswith("research:apple_inc:"), f"Unexpected cache key: {key}"


@pytest.mark.asyncio
async def test_redis_cache_hit_skips_llm():
    """Second call with cached Redis value returns immediately without invoking the graph."""
    from app.core.config import settings
    from app.agents.research.agent import run_research_agent_cached

    cached_json = json.dumps(_STUB_FINDINGS).encode()
    redis_mock = _make_redis_mock(cached_value=cached_json)
    MockLLM = _make_llm_mock()
    llm_instantiated = []

    class _TrackingLLM(MockLLM):
        def __init__(self, *a, **kw):
            llm_instantiated.append(1)
            super().__init__(*a, **kw)

    with patch.object(settings, "USE_RESEARCH_STUBS", True), \
         patch("app.agents.research.agent.get_redis", AsyncMock(return_value=redis_mock)), \
         patch("app.agents.research.agent.ChatOpenAI", _TrackingLLM):

        findings = await run_research_agent_cached("Apple Inc", "deal-001", "tenant-001")

    assert findings == _STUB_FINDINGS, "Cache hit should return exact cached findings"
    assert not llm_instantiated, "LLM must NOT be instantiated on cache hit"
    redis_mock.setex.assert_not_called()


@pytest.mark.asyncio
async def test_tool_call_count_within_limit():
    """tool_call_count must be <= 12 after a full run."""
    from app.core.config import settings
    from app.agents.research.agent import run_research_agent_cached, build_research_graph

    redis_mock = _make_redis_mock(cached_value=None)
    MockLLM = _make_llm_mock()

    with patch.object(settings, "USE_RESEARCH_STUBS", True), \
         patch("app.agents.research.agent.get_redis", AsyncMock(return_value=redis_mock)), \
         patch("app.agents.research.agent.ChatOpenAI", MockLLM):

        from app.agents.research.agent import build_research_graph, ResearchState
        graph = build_research_graph()
        initial: ResearchState = {
            "target_company": "Apple Inc",
            "deal_room_id": "deal-001",
            "tenant_id": "tenant-001",
            "messages": [],
            "research_findings": {},
            "tool_call_count": 0,
            "sufficient": False,
            "tool_call_cache": {},
        }
        result = await graph.ainvoke(initial)

    assert result["tool_call_count"] <= 12, (
        f"tool_call_count {result['tool_call_count']} exceeds limit of 12"
    )


@pytest.mark.asyncio
async def test_parallel_tools_faster_than_sequential():
    """
    Running get_financial_data, get_news_sentiment, get_regulatory_filings concurrently
    should be faster than running them sequentially.
    """
    import asyncio
    from app.core.config import settings
    from app.agents.research.tools import get_financial_data, get_news_sentiment, get_regulatory_filings

    DELAY = 0.1  # seconds each stub "takes"

    async def _slow_tool(original_fn, args: dict, delay: float = DELAY) -> str:
        await asyncio.sleep(delay)
        return await original_fn.ainvoke(args)

    with patch.object(settings, "USE_RESEARCH_STUBS", True):
        # Sequential baseline
        t0 = time.monotonic()
        await _slow_tool(get_financial_data, {"ticker_or_company": "Apple"})
        await _slow_tool(get_news_sentiment, {"company_name": "Apple Inc"})
        await _slow_tool(get_regulatory_filings, {"company_name": "Apple Inc"})
        sequential_time = time.monotonic() - t0

        # Parallel
        t1 = time.monotonic()
        await asyncio.gather(
            _slow_tool(get_financial_data, {"ticker_or_company": "Apple"}),
            _slow_tool(get_news_sentiment, {"company_name": "Apple Inc"}),
            _slow_tool(get_regulatory_filings, {"company_name": "Apple Inc"}),
        )
        parallel_time = time.monotonic() - t1

    assert parallel_time < sequential_time * 0.8, (
        f"Parallel ({parallel_time:.3f}s) should be significantly faster than "
        f"sequential ({sequential_time:.3f}s)"
    )


@pytest.mark.asyncio
async def test_tool_output_truncated_at_limit():
    """Tool output longer than 2000*4=8000 chars is truncated with '[truncated]' marker."""
    from app.agents.research.tools import truncate_tool_output

    long_str = "x" * 9000
    result = truncate_tool_output(long_str)
    assert len(result) < 9000
    assert result.endswith("... [truncated]")

    short_str = "y" * 100
    assert truncate_tool_output(short_str) == short_str


@pytest.mark.asyncio
async def test_tool_error_returned_not_raised():
    """When an external tool raises, the tool returns a ToolError JSON (not re-raises)."""
    from app.core.config import settings
    from app.agents.research.tools import web_search

    with patch.object(settings, "USE_RESEARCH_STUBS", False):
        # No tavily key → should raise internally but return ToolError JSON
        result = await web_search.ainvoke({"query": "Apple Inc"})

    parsed = json.loads(result)
    assert "error" in parsed, "Expected 'error' key in ToolError output"
    assert "retryable" in parsed
    assert "tool_name" in parsed
    assert parsed["tool_name"] == "web_search"


@pytest.mark.asyncio
async def test_deduplication_prevents_duplicate_tool_calls():
    """
    Two identical tool calls in the same message: only 1 real execution (tool_call_count=1)
    but 2 ToolMessages are returned (second from in-run cache).
    """
    from app.agents.research.agent import act_node, ResearchState
    from app.core.config import settings

    state: ResearchState = {
        "target_company": "Apple Inc",
        "deal_room_id": "deal-001",
        "tenant_id": "tenant-001",
        "messages": [AIMessage(
            content="",
            tool_calls=[
                {"name": "web_search", "args": {"query": "Apple Inc"}, "id": "c1", "type": "tool_call"},
                {"name": "web_search", "args": {"query": "Apple Inc"}, "id": "c2", "type": "tool_call"},
            ],
        )],
        "research_findings": {},
        "tool_call_count": 0,
        "sufficient": False,
        "tool_call_cache": {},
    }

    with patch.object(settings, "USE_RESEARCH_STUBS", True):
        result = await act_node(state)

    # tool_call_count must be 1 (only one real execution; second was a cache hit)
    assert result["tool_call_count"] == 1, (
        f"Expected tool_call_count=1 (dedup), got {result['tool_call_count']}"
    )
    # Both ToolMessages must still be present in messages
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 2, (
        f"Expected 2 ToolMessages (one real, one from cache), got {len(tool_messages)}"
    )
    # Both responses have the same content (cache returned same result)
    assert tool_messages[0].content == tool_messages[1].content
