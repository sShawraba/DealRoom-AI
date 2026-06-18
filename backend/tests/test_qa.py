"""
Phase 6 Q&A integration tests.

Flow: generate Q&A → verify rows grouped by category → record answer →
send email (mock SMTP) → verify audit log has qa.email_sent with recipient.
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
    patcher = patch(
        "app.routers.management_qa.moderate_content",
        new=AsyncMock(return_value=_NOT_FLAGGED),
    )
    patcher.start()
    yield
    patcher.stop()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register(client: AsyncClient, email: str, tenant: str) -> str:
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "QATest123!",
        "full_name": "QA User",
        "tenant_name": tenant,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


async def _create_room(client: AsyncClient, token: str, name: str = "QA Room") -> str:
    resp = await client.post(
        "/api/v1/deal-rooms",
        json={"name": name, "target_company": "Target QA Co"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _get_user_id(db: asyncpg.Connection, email: str) -> str:
    row = await db.fetchrow("SELECT id FROM users WHERE email = $1", email)
    assert row is not None
    return str(row["id"])


async def _get_tenant_id(db: asyncpg.Connection, email: str) -> str:
    row = await db.fetchrow("SELECT tenant_id FROM users WHERE email = $1", email)
    assert row is not None
    return str(row["tenant_id"])


async def _seed_report_with_findings(
    db: asyncpg.Connection, tenant_id: str, deal_room_id: str, created_by: str
) -> tuple[str, str]:
    """Seed a report with red_flags and financial_health items."""
    report_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO reports (id, tenant_id, deal_room_id, created_by, status)
        VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, 'draft')
        """,
        report_id, tenant_id, deal_room_id, created_by,
    )
    item_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO report_items (id, report_id, tenant_id, section_type, content, item_index)
        VALUES
          ($1::uuid, $2::uuid, $3::uuid, 'red_flags', 'Unresolved litigation risk in subsidiary.', 0),
          ($4::uuid, $2::uuid, $3::uuid, 'financial_health', 'EBITDA margin declining 3 years.', 1)
        """,
        item_id, report_id, tenant_id,
        str(uuid.uuid4()),
    )
    return report_id, item_id


_MOCK_LLM_RESPONSE = """{
  "categories": [
    {
      "name": "legal",
      "questions": [
        {
          "question": "What is the current status of the subsidiary litigation?",
          "priority": "critical",
          "source_item_id": "00000000-0000-0000-0000-000000000001"
        }
      ]
    },
    {
      "name": "financial",
      "questions": [
        {
          "question": "What actions are planned to reverse the declining EBITDA margin?",
          "priority": "high",
          "source_item_id": "00000000-0000-0000-0000-000000000002"
        }
      ]
    }
  ]
}"""


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_qa(app_client: AsyncClient, db_session: asyncpg.Connection):
    """Generate Q&A returns rows grouped by category."""
    EMAIL = "qa_gen@qa.com"
    token = await _register(app_client, EMAIL, "Firm QA Gen")
    tenant_id = await _get_tenant_id(db_session, EMAIL)
    user_id = await _get_user_id(db_session, EMAIL)
    room_id = await _create_room(app_client, token, "QA Gen Room")
    report_id, _ = await _seed_report_with_findings(db_session, tenant_id, room_id, user_id)

    mock_choice = AsyncMock()
    mock_choice.choices = [AsyncMock()]
    mock_choice.choices[0].message.content = _MOCK_LLM_RESPONSE

    with patch("app.routers.management_qa.AsyncOpenAI") as MockOpenAI:
        mock_client = AsyncMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_choice)

        resp = await app_client.post(
            f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/qa/generate",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["generated"] == 2
    categories = {q["category"] for q in data["questions"]}
    assert "legal" in categories
    assert "financial" in categories


@pytest.mark.asyncio
async def test_list_qa_paginated(app_client: AsyncClient, db_session: asyncpg.Connection):
    """GET /qa returns paginated questions, filterable by category."""
    EMAIL = "qa_list@qa.com"
    token = await _register(app_client, EMAIL, "Firm QA List")
    tenant_id = await _get_tenant_id(db_session, EMAIL)
    user_id = await _get_user_id(db_session, EMAIL)
    room_id = await _create_room(app_client, token, "QA List Room")
    report_id, _ = await _seed_report_with_findings(db_session, tenant_id, room_id, user_id)

    mock_choice = AsyncMock()
    mock_choice.choices = [AsyncMock()]
    mock_choice.choices[0].message.content = _MOCK_LLM_RESPONSE

    with patch("app.routers.management_qa.AsyncOpenAI") as MockOpenAI:
        mock_client = AsyncMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_choice)
        await app_client.post(
            f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/qa/generate",
            headers={"Authorization": f"Bearer {token}"},
        )

    resp = await app_client.get(
        f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/qa",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] >= 2

    # Filter by category
    resp = await app_client.get(
        f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/qa?category=legal",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert all(q["category"] == "legal" for q in resp.json()["items"])


@pytest.mark.asyncio
async def test_record_answer(app_client: AsyncClient, db_session: asyncpg.Connection):
    """PATCH /management-questions/{id}/answer records the response."""
    EMAIL = "qa_ans@qa.com"
    token = await _register(app_client, EMAIL, "Firm QA Answer")
    tenant_id = await _get_tenant_id(db_session, EMAIL)
    user_id = await _get_user_id(db_session, EMAIL)
    room_id = await _create_room(app_client, token, "QA Answer Room")
    report_id, _ = await _seed_report_with_findings(db_session, tenant_id, room_id, user_id)

    mock_choice = AsyncMock()
    mock_choice.choices = [AsyncMock()]
    mock_choice.choices[0].message.content = _MOCK_LLM_RESPONSE

    with patch("app.routers.management_qa.AsyncOpenAI") as MockOpenAI:
        mock_client = AsyncMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_choice)
        gen_resp = await app_client.post(
            f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/qa/generate",
            headers={"Authorization": f"Bearer {token}"},
        )

    question_id = gen_resp.json()["questions"][0]["id"]

    resp = await app_client.patch(
        f"/api/v1/management-questions/{question_id}/answer",
        json={"answer_notes": "We have initiated mediation for the litigation."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["answered"] is True
    assert "mediation" in resp.json()["answer_notes"]


@pytest.mark.asyncio
async def test_send_qa_email_and_audit_log(
    app_client: AsyncClient, db_session: asyncpg.Connection
):
    """send-email triggers SMTP and writes qa.email_sent audit row with recipient."""
    EMAIL = "qa_email@qa.com"
    RECIPIENT = "target@acme.com"
    token = await _register(app_client, EMAIL, "Firm QA Email")
    tenant_id = await _get_tenant_id(db_session, EMAIL)
    user_id = await _get_user_id(db_session, EMAIL)
    room_id = await _create_room(app_client, token, "QA Email Room")
    report_id, _ = await _seed_report_with_findings(db_session, tenant_id, room_id, user_id)

    mock_choice = AsyncMock()
    mock_choice.choices = [AsyncMock()]
    mock_choice.choices[0].message.content = _MOCK_LLM_RESPONSE

    with patch("app.routers.management_qa.AsyncOpenAI") as MockOpenAI:
        mock_client = AsyncMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_choice)
        await app_client.post(
            f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/qa/generate",
            headers={"Authorization": f"Bearer {token}"},
        )

    with patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        resp = await app_client.post(
            f"/api/v1/deal-rooms/{room_id}/reports/{report_id}/qa/send-email",
            json={"recipient_email": RECIPIENT},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["recipient"] == RECIPIENT
    mock_send.assert_called_once()

    # Verify audit log has qa.email_sent with recipient
    rows = await db_session.fetch(
        "SELECT metadata FROM audit_log WHERE action = 'qa.email_sent' AND actor_email = $1",
        EMAIL,
    )
    assert len(rows) >= 1
    import json
    raw_meta = rows[0]["metadata"]
    meta = json.loads(raw_meta) if isinstance(raw_meta, str) else dict(raw_meta)
    assert meta.get("recipient") == RECIPIENT
