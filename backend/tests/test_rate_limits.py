"""
Rate-limit tests — verify slowapi limits on login and document download.

Sends rapid back-to-back requests and asserts the limiter returns 429 on breach.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_rate_limit(app_client: AsyncClient) -> None:
    """6th login attempt from same IP within a minute must return 429."""
    # Register a fresh account so we have valid credentials
    await app_client.post(
        "/api/v1/auth/register",
        json={
            "email": "ratelimit_user@testfirm.com",
            "password": "testpass123",
            "full_name": "Rate Limit User",
            "tenant_name": "Rate Limit Firm",
        },
    )

    last_status = None
    for i in range(6):
        resp = await app_client.post(
            "/api/v1/auth/login",
            json={"email": "ratelimit_user@testfirm.com", "password": "testpass123"},
        )
        last_status = resp.status_code

    assert last_status == 429, (
        f"Expected 429 on the 6th login request, got {last_status}"
    )


@pytest.mark.asyncio
async def test_register_rate_limit(app_client: AsyncClient) -> None:
    """4th registration attempt from same IP within a minute must return 429."""
    last_status = None
    for i in range(4):
        resp = await app_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"rl_reg_{i}@testfirm.com",
                "password": "testpass123",
                "full_name": f"RL Reg {i}",
                "tenant_name": f"RL Firm {i}",
            },
        )
        last_status = resp.status_code

    assert last_status == 429, (
        f"Expected 429 on the 4th register request, got {last_status}"
    )
