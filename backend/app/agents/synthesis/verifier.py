"""CRAG citation verifier — parses [SOURCE: ...] patterns and flags uncited items."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

log = structlog.get_logger(__name__)

CITATION_PATTERN = re.compile(r'\[SOURCE:\s*([^,\]]+),\s*p\.(\d+)\]')


@dataclass
class VerificationResult:
    coverage_pct: float
    uncited_item_ids: list[str] = field(default_factory=list)
    hallucinated_citations: list[str] = field(default_factory=list)


def verify_citations(
    sections: dict[str, list],
    retrieved_chunk_ids: set[str],
) -> VerificationResult:
    """
    Walk all section items, parse [SOURCE: ...] citations, check against retrieved_chunk_ids.
    Items without a citation OR whose chunk_id wasn't retrieved are marked is_verified=False.
    """
    total = 0
    cited = 0
    hallucinated: list[str] = []
    uncited: list[str] = []

    for section_items in sections.values():
        for item in section_items:
            total += 1
            citation = getattr(item, "citation", None) or (
                item.get("citation") if isinstance(item, dict) else None
            )
            chunk_id = None
            if citation:
                chunk_id = (
                    citation.get("chunk_id") if isinstance(citation, dict) else None
                )

            if chunk_id and str(chunk_id) in retrieved_chunk_ids:
                cited += 1
            elif chunk_id:
                hallucinated.append(str(chunk_id))
                _set_unverified(item)
            else:
                item_id = _get_id(item)
                uncited.append(item_id)
                _set_unverified(item)

    coverage = cited / total if total > 0 else 0.0
    if coverage < 0.90:
        log.warning("rag.low_coverage", coverage=round(coverage, 3), total=total, cited=cited)
    else:
        log.info("rag.citation_coverage", coverage=round(coverage, 3), total=total)

    return VerificationResult(
        coverage_pct=coverage,
        uncited_item_ids=uncited,
        hallucinated_citations=hallucinated,
    )


def _set_unverified(item) -> None:
    if isinstance(item, dict):
        item["is_verified"] = False
    else:
        item.is_verified = False


def _get_id(item) -> str:
    if isinstance(item, dict):
        return str(item.get("id", ""))
    return str(getattr(item, "id", ""))
