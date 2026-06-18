"""
Prompt regression tests — validate synthesis output structure against golden fixture.

The golden fixture (tests/fixtures/synthesis_output_golden.json) is the source of
truth for the expected output shape. These tests do NOT call the LLM; they verify
that fixture files committed to the repo match the required schema so that any
structural regressions fail in CI before they reach production.
"""
import json
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthesis_output_golden.json"

EXPECTED_SECTIONS = {
    "executive_summary",
    "financial_health",
    "legal_flags",
    "commercial_assessment",
    "red_flags",
    "key_questions",
}


@pytest.fixture(scope="module")
def golden() -> dict:
    assert FIXTURE_PATH.exists(), f"Golden fixture not found: {FIXTURE_PATH}"
    return json.loads(FIXTURE_PATH.read_text())


def test_all_six_sections_present(golden: dict) -> None:
    sections = golden.get("sections", {})
    missing = EXPECTED_SECTIONS - set(sections.keys())
    assert not missing, f"Missing sections in golden fixture: {missing}"


def test_no_section_is_empty(golden: dict) -> None:
    sections = golden["sections"]
    for name, items in sections.items():
        assert len(items) >= 1, f"Section '{name}' has no items"


def test_all_items_have_citation(golden: dict) -> None:
    sections = golden["sections"]
    for section_name, items in sections.items():
        for i, item in enumerate(items):
            assert "citation" in item, (
                f"Item {i} in section '{section_name}' is missing 'citation' field"
            )
            assert item["citation"] is not None, (
                f"Item {i} in section '{section_name}' has null citation"
            )


def test_all_items_have_content(golden: dict) -> None:
    sections = golden["sections"]
    for section_name, items in sections.items():
        for i, item in enumerate(items):
            assert "content" in item and item["content"], (
                f"Item {i} in section '{section_name}' has empty content"
            )


def test_citation_has_source_and_page(golden: dict) -> None:
    sections = golden["sections"]
    for section_name, items in sections.items():
        for i, item in enumerate(items):
            citation = item.get("citation") or {}
            assert "source" in citation, (
                f"Citation of item {i} in '{section_name}' missing 'source'"
            )
            assert "page" in citation, (
                f"Citation of item {i} in '{section_name}' missing 'page'"
            )
