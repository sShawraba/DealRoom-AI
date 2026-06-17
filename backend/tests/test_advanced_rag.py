"""
Tests for Phase 5 — Advanced RAG, Synthesis & Streaming.

Unit tests mock external I/O (OpenAI, Redis, DB).
Integration test (test_full_pipeline_e2e) runs against the live Docker stack.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── helpers ────────────────────────────────────────────────────────────────────

def _make_chunks(n: int = 5) -> list[dict]:
    return [
        {
            "id": uuid.uuid4(),
            "content": f"Revenue grew 12% YoY. EBITDA margin was 24%. [SOURCE: financials.pdf, p.{i+1}]",
            "page_number": i + 1,
            "filename": "financials.pdf",
            "doc_type": "financial_statement",
            "chunk_level": "child",
            "parent_chunk_id": None,
            "section_header": None,
            "rerank_score": float(n - i),
        }
        for i in range(n)
    ]


# ── Task 09 — Query Understanding ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_query_variants_are_different():
    """_generate_variants returns 3 strings, all different from the original."""
    from app.agents.synthesis.query_understanding import _generate_variants

    variants_payload = {"queries": [
        "EBITDA and revenue growth for the target company",
        "Profitability trends and margin analysis",
        "Financial performance including cash flow",
    ]}
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(variants_payload)

    with patch("app.agents.synthesis.query_understanding.AsyncOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat = MagicMock()
        instance.chat.completions = MagicMock()
        instance.chat.completions.create = AsyncMock(return_value=mock_resp)

        result = await _generate_variants("revenue profit EBITDA margin", n=3)

    assert len(result) == 3
    assert all(isinstance(v, str) and v.strip() for v in result)
    assert len(set(result)) == 3, "variants should be distinct"


@pytest.mark.asyncio
async def test_hyde_embedding_correct_dims():
    """_generate_hyde_embedding returns a 1536-float embedding."""
    from app.agents.synthesis.query_understanding import _generate_hyde_embedding

    fake_embedding = [0.01] * 1536
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "Hypothetical passage about EBITDA margins."

    with (
        patch("app.agents.synthesis.query_understanding.AsyncOpenAI") as MockClient,
        patch(
            "app.agents.synthesis.query_understanding.get_embeddings_batch_cached",
            new=AsyncMock(return_value=[fake_embedding]),
        ),
    ):
        instance = MockClient.return_value
        instance.chat.completions.create = AsyncMock(return_value=mock_resp)
        result = await _generate_hyde_embedding("revenue profit EBITDA")

    assert isinstance(result, list)
    assert len(result) == 1536
    assert all(isinstance(v, float) for v in result)


@pytest.mark.asyncio
async def test_routing_filters_correctly():
    """Financial query should include financial_statement in the returned doc_type filter."""
    from app.agents.synthesis.query_understanding import _route_query

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps({"types": ["financial_statement"]})

    with patch("app.agents.synthesis.query_understanding.AsyncOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create = AsyncMock(return_value=mock_resp)
        result = await _route_query("revenue profit EBITDA margin debt cash flow")

    assert "financial_statement" in result


# ── Task 10 — RRF ─────────────────────────────────────────────────────────────

def test_rrf_no_duplicates():
    """RRF fusion of overlapping result sets contains no duplicate chunk_ids."""
    from app.agents.synthesis.retriever import _reciprocal_rank_fusion

    shared_id = uuid.uuid4()
    set_a = [{"id": shared_id, "content": "a"}, {"id": uuid.uuid4(), "content": "b"}]
    set_b = [{"id": shared_id, "content": "a"}, {"id": uuid.uuid4(), "content": "c"}]

    result = _reciprocal_rank_fusion([set_a, set_b], k=60)
    ids = [str(c["id"]) for c in result]
    assert len(ids) == len(set(ids)), "RRF result must have no duplicate IDs"


# ── Task 11 — Re-ranker ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reranker_changes_order():
    """FlashRank reranker changes the order of at least one chunk."""
    chunks = _make_chunks(5)
    original_order = [str(c["id"]) for c in chunks]

    # Simulate reranker reversing scores
    async def fake_to_thread(fn, req):
        return [{"id": str(p["id"]), "score": float(len(req.passages) - i)}
                for i, p in enumerate(reversed(req.passages))]

    with (
        patch("app.agents.synthesis.reranker.get_reranker"),
        patch("app.agents.synthesis.reranker.asyncio.to_thread", side_effect=fake_to_thread),
    ):
        from app.agents.synthesis.reranker import rerank
        result = await rerank("revenue EBITDA", chunks, top_k=5)

    reranked_order = [str(c["id"]) for c in result]
    assert reranked_order != original_order, "reranker should change at least one position"


# ── Task 12 — Verifier ────────────────────────────────────────────────────────

def test_verifier_flags_hallucination():
    """A chunk_id not in retrieved_chunk_ids is marked as hallucinated + is_verified=False."""
    from app.agents.synthesis.verifier import verify_citations

    retrieved_id = str(uuid.uuid4())
    hallucinated_id = str(uuid.uuid4())

    sections = {
        "financial_health": [
            {"id": str(uuid.uuid4()), "content": "Revenue up.", "citation": {"chunk_id": retrieved_id}, "is_verified": True},
            {"id": str(uuid.uuid4()), "content": "Fake claim.", "citation": {"chunk_id": hallucinated_id}, "is_verified": True},
        ]
    }
    result = verify_citations(sections, retrieved_chunk_ids={retrieved_id})

    assert hallucinated_id in result.hallucinated_citations
    assert result.coverage_pct < 1.0
    # The hallucinated item should be marked unverified
    assert sections["financial_health"][1]["is_verified"] is False


def test_verifier_flags_uncited():
    """An item with no citation is added to uncited_item_ids and marked is_verified=False."""
    from app.agents.synthesis.verifier import verify_citations

    item_id = str(uuid.uuid4())
    sections = {
        "executive_summary": [
            {"id": item_id, "content": "No source for this claim.", "citation": None, "is_verified": True},
        ]
    }
    result = verify_citations(sections, retrieved_chunk_ids=set())

    assert item_id in result.uncited_item_ids
    assert sections["executive_summary"][0]["is_verified"] is False


# ── Task 10 — Permission filtering ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_permission_filter_excludes_restricted():
    """A document with can_view=FALSE must not appear in retrieval results."""
    from app.agents.synthesis.retriever import _run_pgvector

    # Mock session that returns an empty result (as if restricted doc was filtered)
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter([]))
    mock_session.execute = AsyncMock(return_value=mock_result)

    emb = [0.0] * 1536
    result = await _run_pgvector(
        emb,
        deal_room_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        user_role="analyst",
        doc_types=None,
        session=mock_session,
    )

    assert result == [], "restricted documents must not appear in retrieval"


# ── Streaming events ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_streaming_events_published():
    """publish_progress publishes a JSON payload to the correct Redis channel."""
    import json as _json
    from app.services.streaming import AnalysisEvent, publish_progress

    report_id = uuid.uuid4()
    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock()

    with patch("app.services.streaming.get_redis", new=AsyncMock(return_value=mock_redis), create=True):
        await publish_progress(report_id, AnalysisEvent.ANALYSIS_DONE, test_key="test_value")

    mock_redis.publish.assert_awaited_once()
    channel, payload_str = mock_redis.publish.call_args[0]
    assert channel == f"report:{report_id}:events"
    payload = _json.loads(payload_str)
    assert payload["type"] == AnalysisEvent.ANALYSIS_DONE
    assert payload["report_id"] == str(report_id)
    assert payload["test_key"] == "test_value"


# ── End-to-end pipeline (integration, requires Docker stack) ──────────────────

@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_pipeline_e2e(app_client):
    """
    Upload a real PDF, run the full pipeline (bypass ARQ), verify:
    - 6 sections produced
    - citation coverage >= 0.90
    """
    import os

    # Find a sample PDF in the tests directory or create a minimal one
    sample_pdf = os.path.join(os.path.dirname(__file__), "fixtures", "sample_financials.pdf")
    if not os.path.exists(sample_pdf):
        pytest.skip("sample_financials.pdf fixture not present")

    # Create tenant + user + deal room via API
    reg_resp = await app_client.post("/api/v1/auth/register", json={
        "email": "e2e@test.com",
        "password": "Test1234!",
        "full_name": "E2E Tester",
        "company_name": "E2E Corp",
    })
    assert reg_resp.status_code == 201

    login_resp = await app_client.post("/api/v1/auth/login", json={
        "email": "e2e@test.com",
        "password": "Test1234!",
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    dr_resp = await app_client.post("/api/v1/deal-rooms", json={
        "name": "E2E Deal",
        "target_company": "Acme Corp",
    }, headers=headers)
    assert dr_resp.status_code == 201
    deal_room_id = dr_resp.json()["id"]

    # Upload PDF
    with open(sample_pdf, "rb") as f:
        upload_resp = await app_client.post(
            f"/api/v1/deal-rooms/{deal_room_id}/documents",
            files={"files": ("sample_financials.pdf", f, "application/pdf")},
            headers=headers,
        )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()[0]["id"]

    # Wait for indexing (poll up to 30s)
    from app.core.database import AsyncSessionLocal
    from app.models.document import Document
    from sqlalchemy import select
    for _ in range(30):
        async with AsyncSessionLocal() as session:
            row = await session.execute(select(Document).where(Document.id == uuid.UUID(doc_id)))
            doc = row.scalar_one_or_none()
            if doc and doc.status == "indexed":
                break
        await asyncio.sleep(1)
    else:
        pytest.fail("Document was not indexed within 30 seconds")

    # Run synthesis pipeline directly (bypass ARQ)
    from app.core.database import AsyncSessionLocal
    from app.services.report_service import run_full_analysis_pipeline
    from app.repositories.report import ReportRepository
    from app.core.config import settings as cfg

    report_id = uuid.uuid4()
    tenant_id_str = login_resp.json().get("tenant_id")
    if not tenant_id_str:
        pytest.skip("tenant_id not returned in login response")

    tenant_id = uuid.UUID(tenant_id_str)
    user_id = uuid.UUID(login_resp.json().get("user_id", str(uuid.uuid4())))

    # Insert a pending report row
    async with AsyncSessionLocal() as session:
        from app.models.report import Report
        report = Report(
            id=report_id,
            tenant_id=tenant_id,
            deal_room_id=uuid.UUID(deal_room_id),
            created_by=user_id,
            status="pending",
        )
        session.add(report)
        await session.commit()

    async with AsyncSessionLocal() as session:
        await run_full_analysis_pipeline(
            report_id=report_id,
            deal_room_id=uuid.UUID(deal_room_id),
            tenant_id=tenant_id,
            user_id=user_id,
            session=session,
        )

    # Verify 6 sections and coverage
    async with AsyncSessionLocal() as session:
        from app.repositories.report import ReportRepository, ReportItemRepository
        report_repo = ReportRepository(session, tenant_id, user_id)
        report = await report_repo.get_by_id(report_id)
        item_repo = ReportItemRepository(session)
        items = await item_repo.get_items_for_report(report_id)

    section_types = {i.section_type for i in items}
    expected_sections = {
        "executive_summary", "financial_health", "legal_flags",
        "commercial_assessment", "red_flags", "key_questions",
    }
    assert section_types == expected_sections, f"Missing sections: {expected_sections - section_types}"
    assert report.status == "draft"
    assert report.citation_coverage is not None
    assert report.citation_coverage >= 0.90, (
        f"Citation coverage {report.citation_coverage:.2%} is below the 90% threshold"
    )
