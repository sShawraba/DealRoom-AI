import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.minio import get_minio, MinioService
from app.core.redis import get_redis
from redis.asyncio import Redis

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health():
    """Liveness probe — always returns 200 if the process is running."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    minio: MinioService = Depends(get_minio),
):
    """
    Readiness probe — checks DB, Redis, and MinIO connectivity.

    Returns 200 if all three are healthy, 503 if any dependency is down.
    """
    results: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        results["db"] = "ok"
    except Exception as exc:
        log.warning("ready.db_error", error=str(exc))
        results["db"] = "error"

    try:
        await redis.ping()
        results["redis"] = "ok"
    except Exception as exc:
        log.warning("ready.redis_error", error=str(exc))
        results["redis"] = "error"

    try:
        minio.bucket_exists()
        results["minio"] = "ok"
    except Exception as exc:
        log.warning("ready.minio_error", error=str(exc))
        results["minio"] = "error"

    status_code = 200 if all(v == "ok" for v in results.values()) else 503
    return JSONResponse(status_code=status_code, content=results)
