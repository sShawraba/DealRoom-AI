"""Admin router — cache management endpoints."""
from typing import Annotated
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.audit import AuditAction, log_event
from app.core.deps import CurrentUserDep, RedisDep, SessionDep, require_role

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_owner = Depends(require_role("owner"))


@router.delete(
    "/cache/embeddings/{document_id}",
    summary="Invalidate embedding cache for a document",
    description="Removes all Redis embedding cache keys for the given document's chunks. Owner role required.",
    status_code=200,
)
async def invalidate_embeddings_endpoint(
    document_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: Annotated[object, _owner],
) -> dict:
    from app.agents.ingestion.agent import invalidate_embeddings_for_document
    from app.repositories.document import DocumentChunkRepository

    chunk_repo = DocumentChunkRepository(session)
    texts = await chunk_repo.get_text_hashes_for_document(document_id)
    deleted_keys = len(texts)

    await invalidate_embeddings_for_document(document_id, session)

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.CACHE_INVALIDATED,
        resource_type="document",
        resource_id=document_id,
        resource_name=str(document_id),
        request=request,
        metadata={"deleted_keys": deleted_keys, "cache": "embeddings"},
    )
    await session.commit()
    log.info("cache.embeddings_invalidated", document_id=str(document_id), deleted_keys=deleted_keys)
    return {"deleted_keys": deleted_keys}


@router.delete(
    "/cache/research/{company_name}",
    summary="Invalidate research cache for a company",
    description="Removes all date-variant research cache entries for the company. Owner role required.",
    status_code=200,
)
async def invalidate_research_cache_endpoint(
    company_name: str,
    request: Request,
    session: SessionDep,
    current_user: Annotated[object, _owner],
) -> dict:
    from app.agents.research.agent import invalidate_research_cache

    deleted = await invalidate_research_cache(company_name)

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.CACHE_INVALIDATED,
        resource_type="company",
        resource_name=company_name,
        request=request,
        metadata={"deleted_keys": deleted, "cache": "research"},
    )
    await session.commit()
    log.info("cache.research_invalidated", company=company_name, deleted_keys=deleted)
    return {"deleted_keys": deleted}


@router.delete(
    "/cache/ml",
    summary="Invalidate ML risk-score cache",
    description="Removes all ML risk-score cache keys from Redis. Owner role required.",
    status_code=200,
)
async def invalidate_ml_cache_endpoint(
    request: Request,
    session: SessionDep,
    redis: RedisDep,
    current_user: Annotated[object, _owner],
) -> dict:
    keys = await redis.keys("ml:risk:*")
    deleted = 0
    if keys:
        deleted = await redis.delete(*keys)

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.CACHE_INVALIDATED,
        resource_type="ml_cache",
        resource_name="ml:risk:*",
        request=request,
        metadata={"deleted_keys": deleted, "cache": "ml"},
    )
    await session.commit()
    log.info("cache.ml_invalidated", deleted_keys=deleted)
    return {"deleted_keys": deleted}
