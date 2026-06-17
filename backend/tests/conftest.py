"""
Pytest configuration and shared fixtures for Phase 1 tests.

Tests run against the real PostgreSQL + Redis stack inside Docker.
"""
# Patch ForwardRef._evaluate for Python 3.12 compatibility with pydantic v1 compat layer.
# pydantic v1 calls type_._evaluate(globalns, localns, set()) but Python 3.12 made
# `recursive_guard` a required keyword-only arg with no default.
import sys as _sys
if _sys.version_info >= (3, 12):
    import typing as _typing
    _orig_evaluate = _typing.ForwardRef._evaluate

    def _compat_evaluate(self, globalns, localns, type_params=None, *, recursive_guard=frozenset()):
        return _orig_evaluate(self, globalns, localns, type_params, recursive_guard=recursive_guard)

    _typing.ForwardRef._evaluate = _compat_evaluate

import asyncio
import os

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

DB_DSN = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://dealroom:password@db:5432/dealroom",
)

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("VAULT_ADDR", "http://vault:8200")
os.environ.setdefault("VAULT_TOKEN", "dev-root-token")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def clean_db():
    """Truncate all app tables once before the entire test session."""
    conn = await asyncpg.connect(DB_DSN)
    await conn.execute(
        "TRUNCATE document_chunks, documents, audit_log, deal_room_members, "
        "deal_rooms, document_permissions, users, tenants RESTART IDENTITY CASCADE"
    )
    await conn.close()


@pytest_asyncio.fixture
async def db_session():
    """Per-test raw asyncpg connection — avoids SQLAlchemy loop-pinning issues."""
    conn = await asyncpg.connect(DB_DSN)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="session")
async def app_client(clean_db):
    """Session-scoped ASGI test client with Vault secrets pre-loaded."""
    from app.core.vault import load_all_secrets
    from app.core.config import settings
    secrets = load_all_secrets()
    for k, v in secrets.items():
        setattr(settings, k, v)

    from app.core.database import init_db
    from app.core.redis import init_redis
    from app.core.minio import init_minio
    # NullPool avoids asyncpg connections being cached across different event loops
    init_db(settings.database_url, use_null_pool=True)
    init_redis(settings.redis_url)
    init_minio()

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
