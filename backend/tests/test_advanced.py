"""
Phase 7 advanced features integration tests.

Tests:
- compare two deal rooms (200 with both risk scores, red_flag_count correct)
- non-member of one room → 404
- precedent search returns paginated response structure
- restrict document → permissions endpoint returns current grants
- analyst cannot call permissions endpoints (403)
"""
from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient

# ── Helpers ───────────────────────────────────────────────────────────────────

PW = "Adv7Pass!"


def _make_arq_pool_mock():
    mock_job = MagicMock()
    mock_job.job_id = str(uuid.uuid4())
    mock_pool = MagicMock()
    mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
    return AsyncMock(return_value=mock_pool)


def _fake_embedding() -> list[float]:
    return [0.1] * 1536


async def _register(client: AsyncClient, email: str, tenant: str, pw: str = PW) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pw, "full_name": "Test User", "tenant_name": tenant},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


async def _login(client: AsyncClient, email: str, pw: str = PW) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _create_room(client: AsyncClient, token: str, name: str = "Room", target: str = "Corp") -> str:
    resp = await client.post(
        "/api/v1/deal-rooms",
        json={"name": name, "target_company": target},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _invite(client: AsyncClient, owner_token: str, room_id: str, email: str, role: str) -> None:
    resp = await client.post(
        f"/api/v1/deal-rooms/{room_id}/members",
        json={"email": email, "role": role},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 201, resp.text


async def _get_ids(
    db: asyncpg.Connection, email: str
) -> tuple[str, str]:
    """Return (user_id, tenant_id) for the given email."""
    row = await db.fetchrow(
        "SELECT id, tenant_id FROM users WHERE email = $1", email
    )
    assert row is not None, f"User {email} not found"
    return str(row["id"]), str(row["tenant_id"])


async def _seed_approved_report(
    db: asyncpg.Connection,
    tenant_id: str,
    deal_room_id: str,
    created_by: str,
    risk_score: float = 0.65,
    risk_tier: str = "medium",
    red_flag_count: int = 2,
) -> str:
    """Seed an approved report with items; return report_id."""
    report_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO reports (id, tenant_id, deal_room_id, created_by, status, risk_score, risk_tier)
        VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, 'approved', $5, $6)
        """,
        report_id, tenant_id, deal_room_id, created_by, risk_score, risk_tier,
    )
    for i in range(red_flag_count):
        await db.execute(
            """
            INSERT INTO report_items (id, report_id, tenant_id, section_type, content, item_index)
            VALUES ($1::uuid, $2::uuid, $3::uuid, 'red_flags', $4, $5)
            """,
            str(uuid.uuid4()), report_id, tenant_id,
            f"Red flag item {i}", i,
        )
    for i in range(5):
        await db.execute(
            """
            INSERT INTO report_items (id, report_id, tenant_id, section_type, content, item_index)
            VALUES ($1::uuid, $2::uuid, $3::uuid, 'executive_summary', $4, $5)
            """,
            str(uuid.uuid4()), report_id, tenant_id,
            f"Executive summary finding {i}: notable risk", i,
        )
    return report_id


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def adv_db():
    import os
    DB_DSN = os.getenv("TEST_DATABASE_URL", "postgresql://dealroom:password@db:5432/dealroom")
    conn = await asyncpg.connect(DB_DSN)
    yield conn
    await conn.close()


# ── Compare tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compare_two_rooms_returns_both_risk_scores(
    app_client: AsyncClient, adv_db: asyncpg.Connection
):
    """Compare endpoint returns both rooms' risk scores and correct red_flag_count."""
    suffix = uuid.uuid4().hex[:6]
    owner_email = f"cmp_owner_{suffix}@adv.com"
    tenant_name = f"AdvFirm-{suffix}"

    token = await _register(app_client, owner_email, tenant_name)
    owner_id, tenant_id = await _get_ids(adv_db, owner_email)

    room_id_a = await _create_room(app_client, token, "Room Alpha", "AlphaCo")
    room_id_b = await _create_room(app_client, token, "Room Beta", "BetaCo")

    await _seed_approved_report(adv_db, tenant_id, room_id_a, owner_id, risk_score=0.3, risk_tier="low", red_flag_count=1)
    await _seed_approved_report(adv_db, tenant_id, room_id_b, owner_id, risk_score=0.8, risk_tier="high", red_flag_count=3)

    resp = await app_client.get(
        f"/api/v1/deal-rooms/compare?ids={room_id_a},{room_id_b}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "deal_rooms" in data
    assert len(data["deal_rooms"]) == 2

    rooms_by_id = {r["id"]: r for r in data["deal_rooms"]}

    assert rooms_by_id[room_id_a]["risk_score"] == pytest.approx(0.3)
    assert rooms_by_id[room_id_a]["risk_tier"] == "low"
    assert rooms_by_id[room_id_a]["red_flag_count"] == 1

    assert rooms_by_id[room_id_b]["risk_score"] == pytest.approx(0.8)
    assert rooms_by_id[room_id_b]["risk_tier"] == "high"
    assert rooms_by_id[room_id_b]["red_flag_count"] == 3

    assert len(rooms_by_id[room_id_a]["top_findings"]) <= 3
    assert len(rooms_by_id[room_id_b]["top_findings"]) <= 3


@pytest.mark.asyncio
async def test_compare_non_member_gets_404(app_client: AsyncClient):
    """A user who is not a member of one of the rooms receives 404."""
    suffix = uuid.uuid4().hex[:6]

    token_a = await _register(app_client, f"cmp_a_{suffix}@adv.com", f"FirmA-{suffix}")
    token_b = await _register(app_client, f"cmp_b_{suffix}@adv.com", f"FirmB-{suffix}")

    room_id_a = await _create_room(app_client, token_a, "A-Only Room", "CorpA")
    room_id_b = await _create_room(app_client, token_b, "B-Only Room", "CorpB")

    # token_a tries to compare their own room with token_b's room — not a member of B
    resp = await app_client.get(
        f"/api/v1/deal-rooms/compare?ids={room_id_a},{room_id_b}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_compare_requires_exactly_two_ids(app_client: AsyncClient):
    """Providing one or three IDs returns 422."""
    suffix = uuid.uuid4().hex[:6]
    token = await _register(app_client, f"cmp_ids_{suffix}@adv.com", f"FirmIDs-{suffix}")
    room_id = await _create_room(app_client, token, "Single Room", "SingleCo")

    resp = await app_client.get(
        f"/api/v1/deal-rooms/compare?ids={room_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ── Search tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_returns_paginated_response(app_client: AsyncClient):
    """Search endpoint returns PaginatedResponse structure (even if empty results)."""
    suffix = uuid.uuid4().hex[:6]
    token = await _register(app_client, f"srch_{suffix}@adv.com", f"SrchFirm-{suffix}")

    fake_emb = _fake_embedding()
    with patch(
        "app.agents.ingestion.agent.get_embeddings_batch_cached",
        new=AsyncMock(return_value=[fake_emb]),
    ):
        resp = await app_client.get(
            "/api/v1/deal-rooms/search?q=SaaS+low+margin&status=active",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_search_returns_relevant_deals(
    app_client: AsyncClient, adv_db: asyncpg.Connection
):
    """Search returns a deal room when a matching document chunk exists."""
    suffix = uuid.uuid4().hex[:6]
    email = f"srch2_{suffix}@adv.com"
    token = await _register(app_client, email, f"SrchFirm2-{suffix}")
    owner_id, tenant_id = await _get_ids(adv_db, email)

    room_id = await _create_room(app_client, token, "SaaS Deal Room", "SaaSCo")
    doc_id = str(uuid.uuid4())

    await adv_db.execute(
        """
        INSERT INTO documents (id, tenant_id, deal_room_id, uploaded_by, filename, minio_key, status)
        VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, 'test.pdf', 'key/test.pdf', 'indexed')
        """,
        doc_id, tenant_id, room_id, owner_id,
    )

    fake_emb = _fake_embedding()
    emb_str = "[" + ",".join(str(v) for v in fake_emb) + "]"
    await adv_db.execute(
        """
        INSERT INTO document_chunks
            (id, tenant_id, deal_room_id, document_id, chunk_index, content, embedding)
        VALUES (uuid_generate_v4(), $1::uuid, $2::uuid, $3::uuid, 0, 'SaaS low margin risk analysis', $4::vector)
        """,
        tenant_id, room_id, doc_id, emb_str,
    )

    with patch(
        "app.agents.ingestion.agent.get_embeddings_batch_cached",
        new=AsyncMock(return_value=[fake_emb]),
    ):
        resp = await app_client.get(
            "/api/v1/deal-rooms/search?q=SaaS+low+margin",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    ids = [item["id"] for item in data["items"]]
    assert room_id in ids


# ── Permissions tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_restrict_document_and_get_permissions(
    app_client: AsyncClient, adv_db: asyncpg.Connection
):
    """Owner can PATCH permissions to restricted mode and GET the current grants."""
    suffix = uuid.uuid4().hex[:6]
    owner_email = f"perm_owner_{suffix}@adv.com"
    analyst_email = f"perm_analyst_{suffix}@adv.com"
    tenant_name = f"PermFirm-{suffix}"

    owner_token = await _register(app_client, owner_email, tenant_name)
    analyst_token = await _register(app_client, analyst_email, f"{tenant_name}-b")
    owner_id, tenant_id = await _get_ids(adv_db, owner_email)
    analyst_id, _ = await _get_ids(adv_db, analyst_email)

    room_id = await _create_room(app_client, owner_token, "Perm Test Room", "PermCo")

    await adv_db.execute(
        """
        UPDATE users SET tenant_id = $1::uuid WHERE id = $2::uuid
        """,
        tenant_id, analyst_id,
    )
    await adv_db.execute(
        """
        INSERT INTO deal_room_members (id, tenant_id, deal_room_id, user_id, role)
        VALUES (uuid_generate_v4(), $1::uuid, $2::uuid, $3::uuid, 'analyst')
        """,
        tenant_id, room_id, analyst_id,
    )

    doc_id = str(uuid.uuid4())
    await adv_db.execute(
        """
        INSERT INTO documents (id, tenant_id, deal_room_id, uploaded_by, filename, minio_key, status)
        VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, 'sensitive.pdf', 'key/sensitive.pdf', 'indexed')
        """,
        doc_id, tenant_id, room_id, owner_id,
    )
    await adv_db.execute(
        """
        INSERT INTO document_permissions (id, tenant_id, document_id, user_id, can_view, can_download)
        VALUES (uuid_generate_v4(), $1::uuid, $2::uuid, $3::uuid, true, true)
        """,
        tenant_id, doc_id, owner_id,
    )

    # PATCH — restrict to owner-only
    resp = await app_client.patch(
        f"/api/v1/documents/{doc_id}/permissions",
        json={
            "mode": "restricted",
            "grants": [{"user_id": owner_id, "can_view": True, "can_download": True}],
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text
    grants = resp.json()
    assert len(grants) == 1
    assert grants[0]["user_id"] == owner_id
    assert grants[0]["can_view"] is True

    # GET — verify grants are persisted
    resp = await app_client.get(
        f"/api/v1/documents/{doc_id}/permissions",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert any(g["user_id"] == owner_id for g in data)


@pytest.mark.asyncio
async def test_analyst_cannot_modify_permissions(
    app_client: AsyncClient, adv_db: asyncpg.Connection
):
    """Analyst in a deal room gets 403 when trying to update document permissions."""
    suffix = uuid.uuid4().hex[:6]
    owner_email = f"perm2_owner_{suffix}@adv.com"
    analyst_email = f"perm2_analyst_{suffix}@adv.com"
    tenant_name = f"PermFirm2-{suffix}"

    owner_token = await _register(app_client, owner_email, tenant_name)
    analyst_token = await _register(app_client, analyst_email, f"{tenant_name}-x")
    owner_id, tenant_id = await _get_ids(adv_db, owner_email)
    analyst_id, _ = await _get_ids(adv_db, analyst_email)

    room_id = await _create_room(app_client, owner_token, "Analyst Perm Room", "APC")

    await adv_db.execute(
        "UPDATE users SET tenant_id = $1::uuid WHERE id = $2::uuid",
        tenant_id, analyst_id,
    )
    await adv_db.execute(
        """
        INSERT INTO deal_room_members (id, tenant_id, deal_room_id, user_id, role)
        VALUES (uuid_generate_v4(), $1::uuid, $2::uuid, $3::uuid, 'analyst')
        """,
        tenant_id, room_id, analyst_id,
    )

    doc_id = str(uuid.uuid4())
    await adv_db.execute(
        """
        INSERT INTO documents (id, tenant_id, deal_room_id, uploaded_by, filename, minio_key, status)
        VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, 'doc.pdf', 'key/doc.pdf', 'indexed')
        """,
        doc_id, tenant_id, room_id, owner_id,
    )

    analyst_login_resp = await app_client.post(
        "/api/v1/auth/login", json={"email": analyst_email, "password": PW}
    )
    analyst_token_refreshed = analyst_login_resp.json()["access_token"]

    resp = await app_client.patch(
        f"/api/v1/documents/{doc_id}/permissions",
        json={"mode": "restricted", "grants": []},
        headers={"Authorization": f"Bearer {analyst_token_refreshed}"},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_permissions_default_mode_restores_all_members(
    app_client: AsyncClient, adv_db: asyncpg.Connection
):
    """Default mode re-grants permissions to all deal room members."""
    suffix = uuid.uuid4().hex[:6]
    owner_email = f"perm3_owner_{suffix}@adv.com"
    tenant_name = f"PermFirm3-{suffix}"

    owner_token = await _register(app_client, owner_email, tenant_name)
    owner_id, tenant_id = await _get_ids(adv_db, owner_email)

    room_id = await _create_room(app_client, owner_token, "Default Perm Room", "DPC")
    doc_id = str(uuid.uuid4())

    await adv_db.execute(
        """
        INSERT INTO documents (id, tenant_id, deal_room_id, uploaded_by, filename, minio_key, status)
        VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, 'reset.pdf', 'key/reset.pdf', 'indexed')
        """,
        doc_id, tenant_id, room_id, owner_id,
    )

    resp = await app_client.patch(
        f"/api/v1/documents/{doc_id}/permissions",
        json={"mode": "default", "grants": []},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text
    grants = resp.json()
    owner_grant = next((g for g in grants if g["user_id"] == owner_id), None)
    assert owner_grant is not None
    assert owner_grant["can_view"] is True
