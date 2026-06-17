import json
from functools import lru_cache

import structlog
from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.ml import FinancialRatios

log = structlog.get_logger(__name__)

_EXTRACT_PROMPT = (
    "Extract financial ratios from the provided document text.\n\n"
    "Return ONLY valid JSON with these exact keys (use null for missing values):\n"
    "{\n"
    '  "current_ratio": <float|null>,\n'
    '  "debt_to_equity": <float|null>,\n'
    '  "interest_coverage": <float|null>,\n'
    '  "ebitda_margin": <float|null>,\n'
    '  "revenue_growth_yoy": <float|null>,\n'
    '  "cash_burn_rate": <float|null>,\n'
    '  "working_capital_ratio": <float|null>,\n'
    '  "gross_margin": <float|null>\n'
    "}"
)


@lru_cache(maxsize=1)
def _feature_names() -> tuple[str, ...]:
    return (
        "current_ratio",
        "debt_to_equity",
        "interest_coverage",
        "ebitda_margin",
        "revenue_growth_yoy",
        "cash_burn_rate",
        "working_capital_ratio",
        "gross_margin",
    )


async def extract_ratios_from_chunks(chunks: list[str], session=None) -> FinancialRatios:
    """Single gpt-4o-mini call to extract financial ratios from document chunks."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    combined = "\n\n".join(chunks[:20])

    response = await client.chat.completions.create(
        model=settings.CHEAP_MODEL,
        messages=[
            {"role": "system", "content": _EXTRACT_PROMPT},
            {"role": "user", "content": f"Document text:\n{combined}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("ml.features.parse_error", raw=raw[:200])
        data = {}

    return FinancialRatios(**{k: data.get(k) for k in _feature_names()})
