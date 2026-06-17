"""
Audit log tests — verify rows are written and DELETE/UPDATE are blocked at DB level.
"""
import asyncpg
import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, tenant: str) -> str:
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "auditpass99",
        "full_name": "Audit User",
        "tenant_name": tenant,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_register_creates_audit_row(app_client: AsyncClient, db_session: asyncpg.Connection):
    await _register(app_client, "audit_reg@firma.com", "Firm Audit A")
    rows = await db_session.fetch(
        "SELECT action FROM audit_log WHERE action = 'user.registered' AND actor_email = $1",
        "audit_reg@firma.com",
    )
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_login_creates_audit_row(app_client: AsyncClient, db_session: asyncpg.Connection):
    await _register(app_client, "audit_login@firmb.com", "Firm Audit B")
    await app_client.post("/api/v1/auth/login", json={
        "email": "audit_login@firmb.com", "password": "auditpass99"
    })
    rows = await db_session.fetch(
        "SELECT action FROM audit_log WHERE action = 'user.login' AND actor_email = $1",
        "audit_login@firmb.com",
    )
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_deal_room_created_audit_row(app_client: AsyncClient, db_session: asyncpg.Connection):
    token = await _register(app_client, "audit_dr@firmc.com", "Firm Audit C")
    await app_client.post(
        "/api/v1/deal-rooms",
        json={"name": "Audit Room", "target_company": "Target"},
        headers={"Authorization": f"Bearer {token}"},
    )
    rows = await db_session.fetch(
        "SELECT action FROM audit_log WHERE action = 'deal_room.created'"
    )
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_audit_log_delete_permission_denied(db_session: asyncpg.Connection):
    """audit_log must be immutable — DELETE is blocked by trigger."""
    try:
        await db_session.execute("DELETE FROM audit_log WHERE id = -1")
        pytest.fail("Expected error but DELETE succeeded")
    except (asyncpg.exceptions.InsufficientPrivilegeError, asyncpg.exceptions.RaiseError):
        pass  # expected — trigger raises ERRCODE 42501


@pytest.mark.asyncio
async def test_audit_log_update_permission_denied(db_session: asyncpg.Connection):
    """audit_log must be immutable — UPDATE is blocked by trigger."""
    try:
        await db_session.execute("UPDATE audit_log SET action = 'tampered' WHERE id = -1")
        pytest.fail("Expected error but UPDATE succeeded")
    except (asyncpg.exceptions.InsufficientPrivilegeError, asyncpg.exceptions.RaiseError):
        pass  # expected — trigger raises ERRCODE 42501
