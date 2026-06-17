import re

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.audit import AuditAction, log_event
from app.core.deps import SessionDep
from app.core.security import create_access_token, hash_password, verify_password
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, session: SessionDep):
    """Register a new tenant + admin user in one atomic transaction."""
    existing = (
        await session.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    slug = _slugify(body.tenant_name)
    existing_tenant = (
        await session.execute(select(Tenant).where(Tenant.slug == slug))
    ).scalar_one_or_none()
    if existing_tenant:
        slug = f"{slug}-{slug[:6]}"

    tenant = Tenant(name=body.tenant_name, slug=slug)
    session.add(tenant)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role="admin",
    )
    session.add(user)
    await session.flush()

    await log_event(
        session=session,
        actor_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        tenant_id=tenant.id,
        action=AuditAction.USER_REGISTERED,
        resource_type="user",
        resource_id=user.id,
        resource_name=user.email,
        request=request,
    )

    await session.commit()
    log.info("user.registered", email=user.email, tenant=tenant.slug)
    token = create_access_token(user.id, tenant.id, user.role, user.email, user.full_name)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, session: SessionDep):
    """Authenticate user and return JWT."""
    user = (
        await session.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        if user is not None:
            try:
                await log_event(
                    session=session,
                    actor_id=user.id,
                    actor_email=user.email,
                    actor_role=user.role,
                    tenant_id=user.tenant_id,
                    action=AuditAction.USER_LOGIN_FAILED,
                    resource_type="user",
                    resource_id=user.id,
                    resource_name=user.email,
                    request=request,
                )
                await session.commit()
            except Exception:
                await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    await log_event(
        session=session,
        actor_id=user.id,
        actor_email=user.email,
        actor_role=user.role,
        tenant_id=user.tenant_id,
        action=AuditAction.USER_LOGIN,
        resource_type="user",
        resource_id=user.id,
        resource_name=user.email,
        request=request,
    )
    await session.commit()
    log.info("user.login", email=user.email)
    token = create_access_token(user.id, user.tenant_id, user.role, user.email, user.full_name)
    return TokenResponse(access_token=token)
