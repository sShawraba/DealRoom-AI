"""Research Agent — LangGraph ReAct loop for company due diligence."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from datetime import date
from typing import Annotated, Any, Optional

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

try:
    from langgraph.graph import StateGraph, END, add_messages
except ImportError:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages

from typing_extensions import TypedDict

from app.agents.research.tools import (
    get_competitors,
    get_financial_data,
    get_news_sentiment,
    get_regulatory_filings,
    web_search,
)
from app.core.config import settings
from app.core.redis import get_redis

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are a senior M&A research analyst. Research the target company across:\n"
    "1. Recent news (last 90 days)   2. Key financial metrics\n"
    "3. Competitive landscape         4. Risk signals\n"
    "5. Regulatory filings (if public)\n"
    "Use each tool at most once per query. Stop when all 5 areas have findings."
)

_EVAL_PROMPT = (
    "You are evaluating research completeness for M&A due diligence. "
    "Assess whether we have sufficient information across: "
    "news, financials, competitive position, risk signals, regulatory filings.\n"
    "Reply with ONLY valid JSON (no markdown):\n"
    '{"sufficient": true/false, "findings_summary": {'
    '"company_overview": "...", '
    '"recent_news": [...], '
    '"financial_snapshot": {...}, '
    '"competitive_position": "...", '
    '"competitors": [...], '
    '"risk_signals": [...], '
    '"sources_consulted": [...]}}'
)

_ALL_TOOLS = [web_search, get_financial_data, get_news_sentiment, get_competitors, get_regulatory_filings]

# Tools that run in parallel (only need company name)
_PARALLEL_TOOLS = {"get_news_sentiment", "get_financial_data", "get_regulatory_filings"}


# ── State ──────────────────────────────────────────────────────────────────────

class ResearchState(TypedDict):
    target_company: str
    deal_room_id: str
    tenant_id: str
    messages: Annotated[list, add_messages]
    research_findings: dict
    tool_call_count: int
    sufficient: bool
    tool_call_cache: dict  # {"tool_name:arg_hash": result} — prevents duplicate tool calls


# ── Helpers ────────────────────────────────────────────────────────────────────

def _arg_hash(tool_name: str, args: dict) -> str:
    payload = json.dumps({"tool": tool_name, "args": args}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _tool_outputs_summary(messages: list) -> str:
    parts = [
        f"[{msg.name}]: {msg.content[:600]}"
        for msg in messages
        if isinstance(msg, ToolMessage)
    ]
    return "\n".join(parts) if parts else "No tool outputs collected yet."


def _ensure_findings_keys(findings: dict) -> dict:
    list_keys = {"recent_news", "competitors", "risk_signals", "sources_consulted"}
    dict_keys = {"financial_snapshot"}
    str_keys = {"company_overview", "competitive_position"}
    for k in list_keys:
        findings.setdefault(k, [])
    for k in dict_keys:
        findings.setdefault(k, {})
    for k in str_keys:
        findings.setdefault(k, "")
    return findings


# ── Graph nodes ────────────────────────────────────────────────────────────────

async def reason_node(state: ResearchState) -> dict:
    """LLM picks the next tool call(s) to execute."""
    llm = ChatOpenAI(
        model=settings.CHEAP_MODEL,
        api_key=settings.openai_api_key,
        temperature=0,
    ).bind_tools(_ALL_TOOLS)

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Research this company for M&A due diligence: {state['target_company']}"),
        *state["messages"],
    ]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}


async def act_node(state: ResearchState) -> dict:
    """Execute tool calls with parallel execution for independent tools and within-run deduplication."""
    last_msg = state["messages"][-1]
    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return {}

    tool_map = {t.name: t for t in _ALL_TOOLS}
    cache = dict(state.get("tool_call_cache", {}))
    tool_messages: list[ToolMessage] = []
    call_count = state["tool_call_count"]

    parallel_calls: list[dict] = []
    sequential_calls: list[dict] = []
    # (tc, cache_key) for duplicates in THIS batch — filled after execution
    deferred: list[tuple[dict, str]] = []
    # Track keys seen in this batch (before they're cached) to detect within-batch dups
    seen_in_batch: set[str] = set()

    for tc in last_msg.tool_calls:
        cache_key = _arg_hash(tc["name"], tc["args"])
        if cache_key in cache:
            # Hit from a previous run
            log.info("research.tool_dedup_hit", tool=tc["name"], source="cross_run")
            tool_messages.append(ToolMessage(content=cache[cache_key], tool_call_id=tc["id"]))
        elif cache_key in seen_in_batch:
            # Duplicate within this message — defer until first occurrence finishes
            log.info("research.tool_dedup_hit", tool=tc["name"], source="same_batch")
            deferred.append((tc, cache_key))
        else:
            seen_in_batch.add(cache_key)
            if tc["name"] in _PARALLEL_TOOLS:
                parallel_calls.append(tc)
            else:
                sequential_calls.append(tc)

    # Sequential tools (web_search, get_competitors)
    for tc in sequential_calls:
        fn = tool_map.get(tc["name"])
        content = await fn.ainvoke(tc["args"]) if fn else json.dumps({"error": f"Unknown tool: {tc['name']}"})
        cache_key = _arg_hash(tc["name"], tc["args"])
        cache[cache_key] = content
        tool_messages.append(ToolMessage(content=content, tool_call_id=tc["id"]))
        call_count += 1

    # Parallel tools (get_financial_data, get_news_sentiment, get_regulatory_filings)
    if parallel_calls:
        async def _invoke(tc: dict) -> tuple[dict, str]:
            fn = tool_map.get(tc["name"])
            result = await fn.ainvoke(tc["args"]) if fn else json.dumps({"error": f"Unknown tool: {tc['name']}"})
            return tc, result

        results = await asyncio.gather(*[_invoke(tc) for tc in parallel_calls])
        for tc, content in results:
            cache_key = _arg_hash(tc["name"], tc["args"])
            cache[cache_key] = content
            tool_messages.append(ToolMessage(content=content, tool_call_id=tc["id"]))
            call_count += 1

    # Fill deferred duplicates from the now-populated cache
    for tc, cache_key in deferred:
        tool_messages.append(ToolMessage(content=cache[cache_key], tool_call_id=tc["id"]))

    return {
        "messages": tool_messages,
        "tool_call_count": call_count,
        "tool_call_cache": cache,
    }


async def evaluate_node(state: ResearchState) -> dict:
    """LLM evaluates if research is sufficient and extracts structured findings."""
    llm = ChatOpenAI(
        model=settings.CHEAP_MODEL,
        api_key=settings.openai_api_key,
        temperature=0,
    )
    summary = _tool_outputs_summary(state["messages"])
    messages = [
        SystemMessage(content=_EVAL_PROMPT),
        HumanMessage(content=f"Company: {state['target_company']}\n\nResearch collected:\n{summary}"),
    ]
    response = await llm.ainvoke(messages)
    raw = response.content.strip()

    # Strip markdown fences if model adds them
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

    try:
        parsed = json.loads(raw)
        sufficient = bool(parsed.get("sufficient", False))
        findings = parsed.get("findings_summary", {})
    except (json.JSONDecodeError, AttributeError):
        sufficient = state["tool_call_count"] >= 5
        findings = {}

    return {
        "sufficient": sufficient,
        "research_findings": _ensure_findings_keys(findings),
    }


def _after_reason(state: ResearchState) -> str:
    """Route to act if there are tool calls, else skip directly to evaluate."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "act"
    return "evaluate"


def should_continue(state: ResearchState) -> str:
    """After evaluate: END if sufficient or over limit, else loop back to reason."""
    if state.get("sufficient") or state.get("tool_call_count", 0) >= 6:
        return END
    return "reason"


# ── Graph builder ──────────────────────────────────────────────────────────────

def build_research_graph() -> Any:
    graph = StateGraph(ResearchState)
    graph.add_node("reason", reason_node)
    graph.add_node("act", act_node)
    graph.add_node("evaluate", evaluate_node)
    graph.set_entry_point("reason")
    graph.add_conditional_edges("reason", _after_reason, {"act": "act", "evaluate": "evaluate"})
    graph.add_edge("act", "evaluate")
    graph.add_conditional_edges("evaluate", should_continue, {"reason": "reason", END: END})
    return graph.compile()


# ── Public API ─────────────────────────────────────────────────────────────────

async def run_research_agent_cached(
    target_company: str,
    deal_room_id: str,
    tenant_id: str,
) -> dict:
    """
    Run the research agent with Redis caching (key: research:{name}:{YYYY-MM-DD}).
    Returns the cached result immediately on a same-day second call.
    """
    redis = await get_redis()
    normalised = target_company.lower().strip().replace(" ", "_")
    key = f"research:{normalised}:{date.today().isoformat()}"

    cached = await redis.get(key)
    if cached:
        log.info("research.cache_hit", company=target_company, key=key)
        return json.loads(cached)

    try:
        from app.services.streaming import AnalysisEvent, publish_progress
        await publish_progress(deal_room_id, AnalysisEvent.RESEARCH_START)
    except Exception:
        pass

    graph = build_research_graph()
    initial_state: ResearchState = {
        "target_company": target_company,
        "deal_room_id": deal_room_id,
        "tenant_id": tenant_id,
        "messages": [],
        "research_findings": {},
        "tool_call_count": 0,
        "sufficient": False,
        "tool_call_cache": {},
    }

    # LangSmith tracing
    config: dict = {
        "metadata": {"deal_room_id": deal_room_id, "tenant_id": tenant_id},
        "recursion_limit": 80,
    }
    try:
        from langchain.callbacks import LangChainTracer
        tracer = LangChainTracer(project_name="dealroom-research")
        config["callbacks"] = [tracer]
    except Exception:
        pass

    result = None
    try:
        result = await graph.ainvoke(initial_state, config=config)
        findings = result["research_findings"]
    except Exception as exc:
        if "recursion" in str(exc).lower() or "GraphRecursionError" in type(exc).__name__:
            log.warning("research.recursion_limit_hit", company=target_company, error=str(exc))
            findings = initial_state.get("research_findings") or {}
        else:
            raise
    findings = _ensure_findings_keys(findings)

    await redis.setex(key, settings.RESEARCH_CACHE_TTL, json.dumps(findings))
    tool_calls = result["tool_call_count"] if result else 0
    log.info("research.complete", company=target_company, tool_calls=tool_calls)

    try:
        from app.services.streaming import AnalysisEvent, publish_progress
        await publish_progress(
            deal_room_id,
            AnalysisEvent.RESEARCH_DONE,
            company_overview=findings.get("company_overview", ""),
        )
    except Exception:
        pass

    return findings


async def invalidate_research_cache(company_name: str) -> int:
    """Delete all date-variant research cache keys for a company. Returns number of keys deleted."""
    redis = await get_redis()
    normalised = company_name.lower().strip().replace(" ", "_")
    keys = await redis.keys(f"research:{normalised}:*")
    if keys:
        await redis.delete(*keys)
    return len(keys)


# ── Standalone test runner ─────────────────────────────────────────────────────

if __name__ == "__main__":
    from app.core.config import settings as _settings
    from app.core.redis import init_redis
    from app.core.vault import load_all_secrets

    secrets = load_all_secrets()
    for k, v in secrets.items():
        setattr(_settings, k, v)
    init_redis(_settings.redis_url)

    company = sys.argv[1] if len(sys.argv) > 1 else "Apple Inc"
    findings = asyncio.run(run_research_agent_cached(company, "test", "test"))
    print(json.dumps(findings, indent=2))
