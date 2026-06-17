"""Research tools: web search, financials, news, competitors, regulatory filings."""
from __future__ import annotations

import json
from typing import Optional

import structlog
from langchain_core.tools import tool
from pydantic import BaseModel

from app.core.config import settings

log = structlog.get_logger(__name__)

MAX_TOOL_OUTPUT_TOKENS = 2000


def truncate_tool_output(output: str, max_tokens: int = MAX_TOOL_OUTPUT_TOKENS) -> str:
    max_chars = max_tokens * 4
    if len(output) > max_chars:
        return output[:max_chars] + "\n... [truncated]"
    return output


def is_retryable(e: Exception) -> bool:
    return isinstance(e, (TimeoutError, ConnectionError, OSError))


# ── Pydantic output models ─────────────────────────────────────────────────────

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class WebSearchResult(BaseModel):
    results: list[SearchResult]
    query: str
    source: str = "web"


class FinancialSnapshot(BaseModel):
    ticker: Optional[str] = None
    market_cap: Optional[str] = None
    revenue_ttm: Optional[str] = None
    ebitda_margin: Optional[str] = None
    debt_to_equity: Optional[str] = None
    revenue_growth_yoy: Optional[str] = None
    source: str = "yfinance"


class NewsArticle(BaseModel):
    title: str
    url: str
    published_at: str
    sentiment: float


class NewsSentimentResult(BaseModel):
    articles: list[NewsArticle]
    sentiment_score: float
    source: str = "newsapi"


class CompetitorsList(BaseModel):
    competitors: list[str]
    industry: Optional[str] = None
    source: str = "web+llm"


class Filing(BaseModel):
    form: str
    date: str
    description: str
    url: Optional[str] = None


class RegulatoryFilings(BaseModel):
    filings: list[Filing]
    cik: Optional[str] = None
    note: Optional[str] = None
    source: str = "sec_edgar"


class ToolError(BaseModel):
    error: str
    retryable: bool
    tool_name: str


# ── Stub fixtures ──────────────────────────────────────────────────────────────

_STUB_WEB_SEARCH: dict[str, WebSearchResult] = {
    "apple": WebSearchResult(
        results=[SearchResult(
            title="Apple Inc — Company Overview",
            url="https://example.com/apple",
            snippet="Apple Inc. designs, manufactures and markets smartphones, personal computers, "
                    "tablets, wearables and accessories, and sells a variety of related services.",
        )],
        query="Apple Inc",
    ),
    "microsoft": WebSearchResult(
        results=[SearchResult(
            title="Microsoft Corporation — Company Overview",
            url="https://example.com/microsoft",
            snippet="Microsoft is a leading cloud and enterprise software company known for Windows, "
                    "Azure, Microsoft 365, LinkedIn, and GitHub.",
        )],
        query="Microsoft",
    ),
    "tesla": WebSearchResult(
        results=[SearchResult(
            title="Tesla Inc — Company Overview",
            url="https://example.com/tesla",
            snippet="Tesla designs, develops, manufactures, and sells electric vehicles, "
                    "energy generation and storage systems.",
        )],
        query="Tesla",
    ),
}

_STUB_FINANCIALS: dict[str, FinancialSnapshot] = {
    "apple": FinancialSnapshot(
        ticker="AAPL", market_cap="$2.8T", revenue_ttm="$385B",
        ebitda_margin="33%", debt_to_equity="1.5", revenue_growth_yoy="2%",
    ),
    "microsoft": FinancialSnapshot(
        ticker="MSFT", market_cap="$3.1T", revenue_ttm="$227B",
        ebitda_margin="52%", debt_to_equity="0.4", revenue_growth_yoy="16%",
    ),
    "tesla": FinancialSnapshot(
        ticker="TSLA", market_cap="$800B", revenue_ttm="$97B",
        ebitda_margin="14%", debt_to_equity="0.2", revenue_growth_yoy="19%",
    ),
}

_STUB_NEWS: dict[str, NewsSentimentResult] = {
    "apple": NewsSentimentResult(
        articles=[NewsArticle(
            title="Apple reports strong Q4 results, beats estimates",
            url="https://example.com/apple-q4",
            published_at="2024-10-31", sentiment=0.8,
        )],
        sentiment_score=0.7,
    ),
    "microsoft": NewsSentimentResult(
        articles=[NewsArticle(
            title="Microsoft Azure revenues surge on AI demand",
            url="https://example.com/msft-azure",
            published_at="2024-10-31", sentiment=0.9,
        )],
        sentiment_score=0.85,
    ),
    "tesla": NewsSentimentResult(
        articles=[NewsArticle(
            title="Tesla faces increased competition in EV market",
            url="https://example.com/tesla-ev",
            published_at="2024-10-31", sentiment=-0.2,
        )],
        sentiment_score=-0.1,
    ),
}

_STUB_COMPETITORS: dict[str, CompetitorsList] = {
    "apple": CompetitorsList(
        competitors=["Samsung", "Google", "Microsoft", "Meta"],
        industry="Consumer Electronics / Technology",
    ),
    "microsoft": CompetitorsList(
        competitors=["Google", "Amazon", "Apple", "Salesforce"],
        industry="Enterprise Software / Cloud Computing",
    ),
    "tesla": CompetitorsList(
        competitors=["BYD", "GM", "Rivian", "Volkswagen Group"],
        industry="Electric Vehicles / Clean Energy",
    ),
}

_STUB_FILINGS: dict[str, RegulatoryFilings] = {
    "apple": RegulatoryFilings(
        filings=[Filing(
            form="10-K", date="2023-11-03", description="Annual Report",
            url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=AAPL&type=10-K",
        )],
        cik="0000320193",
    ),
    "microsoft": RegulatoryFilings(
        filings=[Filing(
            form="10-K", date="2023-07-27", description="Annual Report",
            url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=MSFT&type=10-K",
        )],
        cik="0000789019",
    ),
    "tesla": RegulatoryFilings(
        filings=[Filing(
            form="10-K", date="2024-01-26", description="Annual Report",
            url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=TSLA&type=10-K",
        )],
        cik="0001318605",
    ),
}


def _stub_key(name: str) -> str:
    lower = name.lower()
    for key in ("apple", "microsoft", "tesla"):
        if key in lower:
            return key
    return "apple"


# ── Tool implementations ───────────────────────────────────────────────────────

@tool
async def web_search(query: str) -> str:
    """Search the web for information about a company or topic."""
    if settings.USE_RESEARCH_STUBS:
        result = _STUB_WEB_SEARCH.get(_stub_key(query), _STUB_WEB_SEARCH["apple"])
        return truncate_tool_output(result.model_dump_json())
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(query=query, max_results=5)
        results = [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", "")[:500],
            )
            for r in response.get("results", [])
        ]
        out = WebSearchResult(results=results, query=query)
        return truncate_tool_output(out.model_dump_json())
    except Exception as e:
        log.warning("tool.web_search_failed", error=str(e))
        return ToolError(error=str(e), retryable=is_retryable(e), tool_name="web_search").model_dump_json()


@tool
async def get_financial_data(ticker_or_company: str) -> str:
    """Get key financial metrics for a company using its ticker symbol or name."""
    if settings.USE_RESEARCH_STUBS:
        result = _STUB_FINANCIALS.get(_stub_key(ticker_or_company), _STUB_FINANCIALS["apple"])
        return truncate_tool_output(result.model_dump_json())
    try:
        import yfinance as yf
        ticker = ticker_or_company.upper()
        info = yf.Ticker(ticker).info
        out = FinancialSnapshot(
            ticker=ticker,
            market_cap=f"${info.get('marketCap', 0) / 1e9:.1f}B" if info.get("marketCap") else None,
            revenue_ttm=f"${info.get('totalRevenue', 0) / 1e9:.1f}B" if info.get("totalRevenue") else None,
            ebitda_margin=f"{info.get('ebitdaMargins', 0) * 100:.1f}%" if info.get("ebitdaMargins") else None,
            debt_to_equity=str(info.get("debtToEquity")) if info.get("debtToEquity") is not None else None,
            revenue_growth_yoy=f"{info.get('revenueGrowth', 0) * 100:.1f}%" if info.get("revenueGrowth") else None,
        )
        return truncate_tool_output(out.model_dump_json())
    except Exception as e:
        log.warning("tool.financial_data_failed", error=str(e))
        return ToolError(error=str(e), retryable=is_retryable(e), tool_name="get_financial_data").model_dump_json()


@tool
async def get_news_sentiment(company_name: str, days_back: int = 90) -> str:
    """Get recent news articles and sentiment score (-1 negative to +1 positive) for a company."""
    if settings.USE_RESEARCH_STUBS:
        result = _STUB_NEWS.get(_stub_key(company_name), _STUB_NEWS["apple"])
        return truncate_tool_output(result.model_dump_json())
    try:
        from newsapi import NewsApiClient
        from datetime import datetime, timedelta
        client = NewsApiClient(api_key=settings.news_api_key)
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        response = client.get_everything(
            q=company_name, from_param=from_date,
            language="en", sort_by="relevancy", page_size=10,
        )
        positive_words = {"surge", "growth", "profit", "beat", "strong", "record", "gain", "rise"}
        negative_words = {"decline", "loss", "fall", "miss", "weak", "down", "risk", "concern"}
        scored: list[NewsArticle] = []
        for a in response.get("articles", []):
            title = a.get("title", "").lower()
            pos = sum(1 for w in positive_words if w in title)
            neg = sum(1 for w in negative_words if w in title)
            sentiment = (pos - neg) / max(pos + neg, 1) if (pos + neg) > 0 else 0.0
            scored.append(NewsArticle(
                title=a.get("title", ""),
                url=a.get("url", ""),
                published_at=a.get("publishedAt", ""),
                sentiment=sentiment,
            ))
        avg = sum(a.sentiment for a in scored) / max(len(scored), 1)
        out = NewsSentimentResult(articles=scored, sentiment_score=avg)
        return truncate_tool_output(out.model_dump_json())
    except Exception as e:
        log.warning("tool.news_sentiment_failed", error=str(e))
        return ToolError(error=str(e), retryable=is_retryable(e), tool_name="get_news_sentiment").model_dump_json()


@tool
async def get_competitors(company_name: str) -> str:
    """Identify the main competitors of a company using LLM extraction."""
    if settings.USE_RESEARCH_STUBS:
        result = _STUB_COMPETITORS.get(_stub_key(company_name), _STUB_COMPETITORS["apple"])
        return truncate_tool_output(result.model_dump_json())
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.CHEAP_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    f"List the top 5 direct competitors of {company_name}. "
                    'Return JSON: {"competitors": ["Company A", ...], "industry": "..."}'
                ),
            }],
            response_format={"type": "json_object"},
            max_tokens=200,
        )
        data = json.loads(response.choices[0].message.content)
        out = CompetitorsList(
            competitors=data.get("competitors", []),
            industry=data.get("industry"),
        )
        return truncate_tool_output(out.model_dump_json())
    except Exception as e:
        log.warning("tool.competitors_failed", error=str(e))
        return ToolError(error=str(e), retryable=is_retryable(e), tool_name="get_competitors").model_dump_json()


@tool
async def get_regulatory_filings(company_name: str) -> str:
    """Get recent SEC EDGAR regulatory filings for a company. Returns empty gracefully for private companies."""
    if settings.USE_RESEARCH_STUBS:
        result = _STUB_FILINGS.get(_stub_key(company_name), _STUB_FILINGS["apple"])
        return truncate_tool_output(result.model_dump_json())
    try:
        import httpx
        search_url = (
            f"https://efts.sec.gov/LATEST/search-index?q=%22{company_name}%22&forms=10-K,10-Q"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                search_url,
                headers={"User-Agent": "DealRoomAI research@dealroom.ai"},
            )
        if resp.status_code != 200:
            out = RegulatoryFilings(
                filings=[], note="Not found in SEC EDGAR (may be a private company)"
            )
            return truncate_tool_output(out.model_dump_json())
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        filings = [
            Filing(
                form=h.get("_source", {}).get("form_type", ""),
                date=h.get("_source", {}).get("file_date", ""),
                description=(h.get("_source", {}).get("display_names") or [""])[0],
                url=f"https://www.sec.gov/Archives/edgar/data/{h.get('_source', {}).get('entity_id', '')}/{h.get('_id', '')}",
            )
            for h in hits[:5]
        ]
        out = RegulatoryFilings(filings=filings)
        return truncate_tool_output(out.model_dump_json())
    except Exception as e:
        log.warning("tool.regulatory_filings_failed", error=str(e))
        return ToolError(error=str(e), retryable=is_retryable(e), tool_name="get_regulatory_filings").model_dump_json()
