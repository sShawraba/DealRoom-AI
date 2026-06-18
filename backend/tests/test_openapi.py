"""
OpenAPI completeness tests — every endpoint must have summary and responses defined.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_openapi_schema_accessible(app_client: AsyncClient) -> None:
    resp = await app_client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    assert "info" in schema


@pytest.mark.asyncio
async def test_all_operations_have_summary(app_client: AsyncClient) -> None:
    """Every operation in the OpenAPI schema must have a summary field."""
    resp = await app_client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    missing_summary: list[str] = []
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method in ("get", "post", "put", "patch", "delete", "head", "options"):
                if not operation.get("summary"):
                    missing_summary.append(f"{method.upper()} {path}")

    assert not missing_summary, (
        f"Operations missing 'summary':\n" + "\n".join(missing_summary)
    )


@pytest.mark.asyncio
async def test_all_operations_have_responses(app_client: AsyncClient) -> None:
    """Every operation must declare at least one response."""
    resp = await app_client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    missing_responses: list[str] = []
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method in ("get", "post", "put", "patch", "delete", "head", "options"):
                if not operation.get("responses"):
                    missing_responses.append(f"{method.upper()} {path}")

    assert not missing_responses, (
        f"Operations missing 'responses':\n" + "\n".join(missing_responses)
    )
