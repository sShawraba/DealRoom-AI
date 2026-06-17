from redis.asyncio import Redis, from_url
from arq.connections import RedisSettings, create_pool

from app.core.config import settings


def _arq_settings() -> RedisSettings:
    """Build ARQ RedisSettings from REDIS_URL."""
    url = settings.redis_url or "redis://redis:6379/0"
    # arq needs host/port/db parsed out
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "redis",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
    )


_redis_client: Redis | None = None


def init_redis(redis_url: str | None = None) -> None:
    """Called once in app lifespan after Vault injects secrets."""
    global _redis_client
    url = redis_url or settings.redis_url
    _redis_client = from_url(url, encoding="utf-8", decode_responses=False)


async def dispose_redis() -> None:
    if _redis_client:
        await _redis_client.aclose()


async def get_redis() -> Redis:
    """FastAPI dependency — returns the shared async Redis client."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialised. Call init_redis() in lifespan.")
    return _redis_client


async def get_arq_pool():
    """Returns an ARQ connection pool for enqueuing jobs."""
    return await create_pool(_arq_settings())
