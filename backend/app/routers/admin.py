"""Admin router — cache management endpoints (full implementation in Phase 9)."""
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends

from app.core.deps import CurrentUserDep, RedisDep, require_role

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/cache/clear", status_code=202)
async def clear_cache():
    """Placeholder: clears application-level Redis caches (Phase 9)."""
    return {"detail": "Cache clear scheduled"}


@router.delete("/cache/research/{company_name}", status_code=200)
async def invalidate_research_cache_endpoint(company_name: str):
    """Delete all date-variant research cache entries for a company."""
    from app.agents.research.agent import invalidate_research_cache
    deleted = await invalidate_research_cache(company_name)
    return {"company_name": company_name, "keys_deleted": deleted}


@router.delete("/cache/ml", status_code=200)
async def invalidate_ml_cache(
    redis: RedisDep,
    current_user: Annotated[object, Depends(require_role("owner"))],
):
    """Delete all ML risk-score cache entries from Redis. Owner role required."""
    keys = await redis.keys("ml:risk:*")
    deleted = 0
    if keys:
        deleted = await redis.delete(*keys)
    log.info("cache.ml_invalidated", keys_deleted=deleted, actor=str(current_user))
    return {"keys_deleted": deleted}
