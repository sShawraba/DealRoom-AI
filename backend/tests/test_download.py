"""
Tests for document download with watermarking and permission enforcement.

Requires the real Docker stack (PostgreSQL + MinIO + Redis).
Reuses session-scoped event_loop and app_client from conftest.py.
"""
from __future__ import annotations

import asyncio
import io
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
import pytest_asyncio

DB_DSN = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://dealroom:password@db:5432/dealroom",
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_arq_pool_mock():
    """Mock for get_arq_pool returning a pool with a string job_id."""
    mock_job = MagicMock()
    mock_job.job_id = str(uuid.uuid4())
    mock_pool = MagicMock()
    mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
    return AsyncMock(return_value=mock_pool)


def _make_pdf() -> bytes:
    """Build a minimal valid PDF using pypdf."""
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    stream_data = (
        "BT\n/F1 12 Tf\n72 700 Td\n(Watermark test document) Tj\nET\n"
    ).encode()
    stream_obj = DecodedStreamObject()
    stream_obj.set_data(stream_data)
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
        })
    })
    page[NameObject("/Contents")] = writer._add_object(stream_obj)

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def dl_db_conn():
    """Per-test asyncpg connection for DB assertions (function-scoped to match test loop)."""
    conn = await asyncpg.connect(DB_DSN)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="session")
async def owner_setup(app_client):
    """Returns (headers, deal_room_id, doc_id) for an owner user."""
    suffix = uuid.uuid4().hex[:6]
    email = f"owner-dl-{suffix}@test.com"

    reg = await app_client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": f"dl-tenant-{suffix}",
            "email": email,
            "full_name": "Owner User",
            "password": "Passw0rd!",
        },
    )
    assert reg.status_code in (200, 201), reg.text

    login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Passw0rd!"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    dr = await app_client.post(
        "/api/v1/deal-rooms",
        json={"name": "Download Room", "target_company": "Beta Corp"},
        headers=headers,
    )
    assert dr.status_code in (200, 201), dr.text
    deal_room_id = dr.json()["id"]

    pdf = _make_pdf()
    with patch("app.routers.documents.get_arq_pool", new=_make_arq_pool_mock()):
        up = await app_client.post(
            f"/api/v1/deal-rooms/{deal_room_id}/documents",
            files=[("files", ("watermark_test.pdf", pdf, "application/pdf"))],
            headers=headers,
        )
    assert up.status_code == 201, up.text
    doc_id = up.json()[0]["id"]

    return headers, deal_room_id, doc_id


# ── tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_owner_can_download_with_watermark(owner_setup, app_client):
    """Owner (can_download=True) receives a valid PDF."""
    headers, deal_room_id, doc_id = owner_setup

    resp = await app_client.get(
        f"/api/v1/deal-rooms/{deal_room_id}/documents/{doc_id}/download",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    # Response should be a valid PDF
    assert resp.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_viewer_without_download_permission_gets_403(
    owner_setup, app_client, dl_db_conn
):
    """A viewer with can_download=False receives HTTP 403."""
    _, deal_room_id, doc_id = owner_setup

    suffix = uuid.uuid4().hex[:6]
    viewer_email = f"viewer-dl-{suffix}@test.com"

    tenant_id = await dl_db_conn.fetchval(
        "SELECT tenant_id FROM documents WHERE id = $1::uuid", doc_id
    )
    viewer_user_id = uuid.uuid4()

    from app.core.security import hash_password

    await dl_db_conn.execute(
        """
        INSERT INTO users (id, tenant_id, email, hashed_password, full_name, role)
        VALUES ($1::uuid, $2::uuid, $3, $4, 'Viewer User', 'viewer')
        """,
        viewer_user_id,
        tenant_id,
        viewer_email,
        hash_password("Passw0rd!"),
    )
    await dl_db_conn.execute(
        """
        INSERT INTO deal_room_members (id, tenant_id, deal_room_id, user_id, role)
        VALUES (uuid_generate_v4(), $1::uuid, $2::uuid, $3::uuid, 'viewer')
        """,
        tenant_id,
        uuid.UUID(deal_room_id),
        viewer_user_id,
    )
    await dl_db_conn.execute(
        """
        INSERT INTO document_permissions
            (id, tenant_id, document_id, user_id, can_view, can_download)
        VALUES (uuid_generate_v4(), $1::uuid, $2::uuid, $3::uuid, true, false)
        """,
        tenant_id,
        uuid.UUID(doc_id),
        viewer_user_id,
    )

    login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": viewer_email, "password": "Passw0rd!"},
    )
    assert login.status_code == 200, login.text
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await app_client.get(
        f"/api/v1/deal-rooms/{deal_room_id}/documents/{doc_id}/download",
        headers=viewer_headers,
    )
    assert resp.status_code == 403, resp.text
