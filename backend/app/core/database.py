from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    return create_async_engine(
        settings.database_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        echo=settings.APP_ENV == "development",
    )


# Deferred — engine is created after Vault loads secrets in lifespan.
_engine = None
_AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str | None = None, *, use_null_pool: bool = False) -> None:
    """Called once in app lifespan after secrets are injected."""
    global _engine, _AsyncSessionLocal
    from sqlalchemy.pool import NullPool
    url = database_url or settings.database_url
    if use_null_pool:
        _engine = create_async_engine(url, poolclass=NullPool, echo=settings.APP_ENV == "development")
    else:
        _engine = create_async_engine(
            url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            echo=settings.APP_ENV == "development",
        )
    _AsyncSessionLocal = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )


async def dispose_db() -> None:
    if _engine:
        await _engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    if _AsyncSessionLocal is None:
        raise RuntimeError("Database not initialised. Call init_db() in lifespan.")
    async with _AsyncSessionLocal() as session:
        yield session


def AsyncSessionLocal() -> AsyncSession:
    """Return a new async session (context manager). Used by background workers."""
    if _AsyncSessionLocal is None:
        raise RuntimeError("Database not initialised. Call init_db() in lifespan.")
    return _AsyncSessionLocal()
