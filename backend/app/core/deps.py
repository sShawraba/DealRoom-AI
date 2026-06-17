"""
Central dependency module — all routers import from here only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.minio import MinioService, get_minio
from app.core.redis import get_arq_pool, get_redis
from app.core.security import decode_token

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: UUID
    tenant_id: UUID
    role: str
    email: str
    full_name: str


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    """Decode the Bearer JWT and return a CurrentUser. Raises 401 on failure."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(
        id=UUID(payload["sub"]),
        tenant_id=UUID(payload["tenant_id"]),
        role=payload["role"],
        email=payload["email"],
        full_name=payload["full_name"],
    )


def require_role(*roles: str):
    """Dependency factory: raises 403 if the current user's tenant-level role is not in *roles*."""

    async def _check(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {list(roles)}",
            )
        return current_user

    return _check


# ── Typed aliases for router injection ────────────────────────────────────────
SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]
MinioDep = Annotated[MinioService, Depends(get_minio)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


async def get_risk_classifier():
    """Returns the loaded risk classifier, or None until Phase 4."""
    try:
        import app.ml.classifier as ml_module
        return getattr(ml_module, "risk_classifier", None)
    except ImportError:
        return None
