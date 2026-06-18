"""
Phase 6 approval workflow integration tests.

Full flow:
  post dispute → try approve (409) → resolve → approve (200) →
  verify report_approvals row → try edit item (409) → try post annotation (409)
  analyst tries approve (403)
"""
import uuid
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from httpx import AsyncClient

from app.core.guardrails import ModerationResult

_NOT_FLAGGED = ModerationResult(flagged=False, categories=[])


@pytest.fixture(autouse=True)
def mock_moderate_content():
    """Stub out OpenAI moderation API for all tests in this module."""
    patcher_ann = patch(
        "app.routers.annotations.moderate_content",
        new=AsyncMock(return_value=_NOT_FLAGGED),
    )
    patcher_rep = patch(
        "app.routers.reports.moderate_content",
        new=AsyncMock(return_value=_NOT_FLAGGED),
    )
    patcher_ann.start()
    patcher_rep.start()
    yield
    patcher_ann.stop()
    patcher_rep.stop()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register(client: AsyncClient, email: str, tenant: str) -> str:
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Approval123!",
        "full_name": "Test User",
        "tenant_name": tenant,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


async def _login(client: AsyncClient, email: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "Approval123!"
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _create_room(client: AsyncClient, token: str) -> str:
    resp = await client.post(
        "/api/v1/deal-rooms",
        json={"name": "Approval Test Room", "target_company": "ACME Corp"},
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


async def _seed_report_and_item(
    db: asyncpg.Connection, tenant_id: str, deal_room_id: str, created_by: str
) -> tuple[str, str]:
    """Inject a draft report + one report_item; return (report_id, item_id)."""
    report_id = str(uuid.uuid4())
    item_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO reports (id, tenant_id, deal_room_id, created_by, status)
        VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, 'draft')
        """,
        report_id, tenant_id, deal_room_id, created_by,
    )
    await db.execute(
        """
        INSERT INTO report_items (id, report_id, tenant_id, section_type, content, item_index)
        VALUES ($1::uuid, $2::uuid, $3::uuid, 'red_flags', 'Suspicious revenue spike Q3', 0)
        """,
        item_id, report_id, tenant_id,
    )
    return report_id, item_id


async def _get_user_id(db: asyncpg.Connection, email: str) -> str:
    row = await db.fetchrow("SELECT id FROM users WHERE email = $1", email)
    assert row is not None, f"User {email} not found"
    return str(row["id"])


async def _get_tenant_id(db: asyncpg.Connection, email: str) -> str:
    row = await db.fetchrow(
        "SELECT u.tenant_id FROM users u WHERE u.email = $1", email
    )
    assert row is not None
    return str(row["tenant_id"])


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_approval_flow(app_client: AsyncClient, db_session: asyncpg.Connection):
    """
    Full happy path:
      post dispute → approve 409 → resolve → approve 200 →
      edit item 409 → post annotation 409
    """
    OWNER_EMAIL = "appr_owner@approval.com"
    SENIOR_EMAIL = "appr_senior@approval.com"
    ANALYST_EMAIL = "appr_analyst@approval.com"
    TENANT = "Firm Approval"

    # Register all users in the same tenant (owner first creates tenant)
    owner_token = await _register(app_client, OWNER_EMAIL, TENANT)

    # Register senior and analyst in same tenant by having owner invite them;
    # they must first self-register to exist in the system.
    # We use a second tenant to bootstrap their accounts, then the real
    # tenant membership will be via the invites from the owner.
    # Since register creates a new tenant, we invite by registering them in the
    # owner's tenant by using the owner's invite flow. But first they need accounts.
    # Workaround: register them in same-named tenant (they get their own tenant),
    # but then we need them in the owner's tenant. The current system doesn't
    # support cross-tenant membership, so instead we seed the DB directly.

    # Simpler approach: seed users in the same tenant via direct DB insert.
    tenant_id = await _get_tenant_id(db_session, OWNER_EMAIL)
    owner_id = await _get_user_id(db_session, OWNER_EMAIL)

    senior_id = str(uuid.uuid4())
    analyst_id = str(uuid.uuid4())
    from app.core.security import hash_password
    from app.core.config import settings
    from app.core.vault import load_all_secrets
    secrets = load_all_secrets()
    for k, v in secrets.items():
        setattr(settings, k, v)

    pwd_hash = hash_password("Approval123!")
    await db_session.execute(
        """
        INSERT INTO users (id, tenant_id, email, hashed_password, full_name, role)
        VALUES ($1::uuid, $2::uuid, $3, $4, 'Senior Analyst', 'analyst'),
               ($5::uuid, $2::uuid, $6, $4, 'Junior Analyst', 'analyst')
        """,
        senior_id, tenant_id, SENIOR_EMAIL, pwd_hash,
        analyst_id, ANALYST_EMAIL,
    )

    # Create deal room (owner)
    room_id = await _create_room(app_client, owner_token)

    # Invite senior and analyst as members
    await _invite(app_client, owner_token, room_id, SENIOR_EMAIL, "senior_analyst")
    await _invite(app_client, owner_token, room_id, ANALYST_EMAIL, "analyst")

    senior_token = await _login(app_client, SENIOR_EMAIL)
    analyst_token = await _login(app_client, ANALYST_EMAIL)

    # Seed report
    report_id, item_id = await _seed_report_and_item(
        db_session, tenant_id, room_id, owner_id
    )

    # Submit for review
    resp = await app_client.post(
        f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/status",
        json={"action": "submit_for_review"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "in_review"

    # Post a disputed annotation (as analyst)
    resp = await app_client.post(
        f"/api/v1/deal-rooms/{room_id}/annotations",
        json={
            "report_item_id": item_id,
            "content": "This revenue spike is not explained in any filing.",
            "type": "disputed",
        },
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 201, resp.text
    annotation_id = resp.json()["id"]
    assert resp.json()["type"] == "disputed"

    # Analyst tries to approve → 403 (not a senior analyst)
    resp = await app_client.post(
        f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/status",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 403, resp.text

    # Senior tries to approve with unresolved dispute → 409
    resp = await app_client.post(
        f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/status",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {senior_token}"},
    )
    assert resp.status_code == 409, resp.text
    assert "disputed annotation" in resp.json()["detail"].lower()

    # Resolve the disputed annotation (senior)
    resp = await app_client.patch(
        f"/api/v1/annotations/{annotation_id}",
        json={"resolved": True},
        headers={"Authorization": f"Bearer {senior_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["resolved"] is True

    # Approve succeeds now
    resp = await app_client.post(
        f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/status",
        json={"action": "approve", "sign_off_notes": "Reviewed and approved."},
        headers={"Authorization": f"Bearer {senior_token}"},
    )
    assert resp.status_code == 200, resp.text
    approval_id = resp.json()["approval_id"]
    assert resp.json()["status"] == "approved"

    # Verify report_approvals row in DB
    row = await db_session.fetchrow(
        "SELECT * FROM report_approvals WHERE id = $1::uuid", approval_id
    )
    assert row is not None
    assert str(row["report_id"]) == report_id

    # Try to edit report item after approval → 409
    resp = await app_client.patch(
        f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/items/{item_id}",
        json={"edited_content": "Attempted edit after approval"},
        headers={"Authorization": f"Bearer {senior_token}"},
    )
    assert resp.status_code == 409, resp.text

    # Try to post annotation after approval → 409
    resp = await app_client.post(
        f"/api/v1/deal-rooms/{room_id}/annotations",
        json={
            "report_item_id": item_id,
            "content": "Annotation after approval",
            "type": "comment",
        },
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_submit_for_review_only_from_draft(app_client: AsyncClient, db_session: asyncpg.Connection):
    """Submitting a non-draft report for review returns 409."""
    OWNER_EMAIL = "appr2_owner@approval.com"
    owner_token = await _register(app_client, OWNER_EMAIL, "Firm Approval 2")
    tenant_id = await _get_tenant_id(db_session, OWNER_EMAIL)
    owner_id = await _get_user_id(db_session, OWNER_EMAIL)
    room_id = await _create_room(app_client, owner_token)

    report_id, _ = await _seed_report_and_item(db_session, tenant_id, room_id, owner_id)

    # Submit successfully
    await app_client.post(
        f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/status",
        json={"action": "submit_for_review"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    # Try again — now in_review, not draft
    resp = await app_client.post(
        f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/status",
        json={"action": "submit_for_review"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_annotation_reply_flow(app_client: AsyncClient, db_session: asyncpg.Connection):
    """Create annotation then reply to it."""
    OWNER_EMAIL = "appr3_owner@approval.com"
    owner_token = await _register(app_client, OWNER_EMAIL, "Firm Approval 3")
    tenant_id = await _get_tenant_id(db_session, OWNER_EMAIL)
    owner_id = await _get_user_id(db_session, OWNER_EMAIL)
    room_id = await _create_room(app_client, owner_token)

    report_id, item_id = await _seed_report_and_item(db_session, tenant_id, room_id, owner_id)

    # Create annotation
    resp = await app_client.post(
        f"/api/v1/deal-rooms/{room_id}/annotations",
        json={"report_item_id": item_id, "content": "Initial comment", "type": "comment"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 201, resp.text
    annotation_id = resp.json()["id"]

    # Reply to annotation
    resp = await app_client.post(
        f"/api/v1/annotations/{annotation_id}/replies",
        json={"content": "Reply to the comment"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["annotation_id"] == annotation_id


@pytest.mark.asyncio
async def test_list_annotations_paginated(app_client: AsyncClient, db_session: asyncpg.Connection):
    """GET /annotations returns grouped + paginated response."""
    OWNER_EMAIL = "appr4_owner@approval.com"
    owner_token = await _register(app_client, OWNER_EMAIL, "Firm Approval 4")
    tenant_id = await _get_tenant_id(db_session, OWNER_EMAIL)
    owner_id = await _get_user_id(db_session, OWNER_EMAIL)
    room_id = await _create_room(app_client, owner_token)

    report_id, item_id = await _seed_report_and_item(db_session, tenant_id, room_id, owner_id)

    for content in ["Comment A", "Comment B"]:
        await app_client.post(
            f"/api/v1/deal-rooms/{room_id}/annotations",
            json={"report_item_id": item_id, "content": content, "type": "comment"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    resp = await app_client.get(
        f"/api/v1/deal-rooms/{room_id}/annotations?page=1&page_size=50",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "annotations" in data
    assert data["total"] >= 2
    assert item_id in data["annotations"]
