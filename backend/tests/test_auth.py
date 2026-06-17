"""Auth endpoint tests — register, login, token validation."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(app_client: AsyncClient):
    resp = await app_client.post("/api/v1/auth/register", json={
        "email": "alice@firmA.com",
        "password": "securepass1",
        "full_name": "Alice Admin",
        "tenant_name": "Firm Alpha",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(app_client: AsyncClient):
    payload = {
        "email": "dup@firmB.com",
        "password": "securepass1",
        "full_name": "Dup User",
        "tenant_name": "Firm Dup",
    }
    await app_client.post("/api/v1/auth/register", json=payload)
    resp = await app_client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_success(app_client: AsyncClient):
    await app_client.post("/api/v1/auth/register", json={
        "email": "bob@firmC.com",
        "password": "mypassword99",
        "full_name": "Bob User",
        "tenant_name": "Firm Charlie",
    })
    resp = await app_client.post("/api/v1/auth/login", json={
        "email": "bob@firmC.com",
        "password": "mypassword99",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(app_client: AsyncClient):
    await app_client.post("/api/v1/auth/register", json={
        "email": "charlie@firmD.com",
        "password": "correctpass1",
        "full_name": "Charlie",
        "tenant_name": "Firm Delta",
    })
    resp = await app_client.post("/api/v1/auth/login", json={
        "email": "charlie@firmD.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(app_client: AsyncClient):
    resp = await app_client.post("/api/v1/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "doesntmatter",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(app_client: AsyncClient):
    resp = await app_client.get("/api/v1/deal-rooms")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_invalid_token(app_client: AsyncClient):
    resp = await app_client.get(
        "/api/v1/deal-rooms",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_contains_tenant_id(app_client: AsyncClient):
    """JWT payload must include tenant_id."""
    import base64, json
    resp = await app_client.post("/api/v1/auth/register", json={
        "email": "dave@firmE.com",
        "password": "pass123456",
        "full_name": "Dave",
        "tenant_name": "Firm Echo",
    })
    token = resp.json()["access_token"]
    # Decode payload (no verification needed — just inspect claims)
    payload_b64 = token.split(".")[1]
    # Pad base64
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    assert "tenant_id" in payload
    assert "sub" in payload
    assert "role" in payload
