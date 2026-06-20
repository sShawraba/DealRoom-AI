from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.limiter import RateLimitExceeded, _rate_limit_exceeded_handler, ip_limiter
from app.core.logging import setup_logging
from app.middleware.request_id import RequestIDMiddleware

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Load secrets from Vault — must happen before anything else.
    try:
        from app.core.vault import load_all_secrets
        secrets = load_all_secrets()
        for key, value in secrets.items():
            setattr(settings, key, value)
        log.info("vault.secrets_loaded", vault=settings.VAULT_ADDR)
    except Exception as exc:
        # If Vault is unreachable the app must fail loudly.
        raise RuntimeError(f"Cannot reach Vault at {settings.VAULT_ADDR}: {exc}") from exc

    # 2. Validate critical secrets are non-empty.
    required = ["secret_key", "database_url", "openai_api_key"]
    missing = [k for k in required if not getattr(settings, k)]
    if missing:
        raise RuntimeError(f"Vault loaded but these secrets are empty: {missing}")

    # 3. Setup logging now that APP_ENV is confirmed.
    setup_logging()

    # 4. Sentry (optional).
    if settings.SENTRY_DSN and settings.SENTRY_DSN.strip():
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment=settings.APP_ENV,
        )
        log.info("sentry.initialised")

    # 5. Initialise DB, Redis, MinIO.
    from app.core.database import init_db, dispose_db
    from app.core.redis import init_redis, dispose_redis
    from app.core.minio import init_minio

    init_db(settings.database_url)
    init_redis(settings.redis_url)
    init_minio()

    # 6. Optionally load ML model if artifact exists.
    if Path(settings.ML_MODEL_PATH).exists():
        try:
            import app.ml.classifier as ml_module
            ml_module.risk_classifier = ml_module.RiskClassifier()
            log.info("ml.model_loaded", path=settings.ML_MODEL_PATH)
        except Exception as exc:
            log.warning("ml.model_load_failed", error=str(exc))

    log.info("startup.complete", env=settings.APP_ENV, vault=settings.VAULT_ADDR)
    yield

    # Teardown
    from app.core.database import dispose_db
    from app.core.redis import dispose_redis
    await dispose_db()
    await dispose_redis()
    log.info("shutdown.complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="DealRoom AI",
        version="0.1.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # Rate limiter state (shared by all @ip_limiter / @user_limiter decorators)
    app.state.limiter = ip_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS
    cors_origins = (
        ["http://localhost:5173"]
        if settings.APP_ENV != "production"
        else []  # set explicitly in production .env
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID — must be added after CORS so it wraps all responses
    app.add_middleware(RequestIDMiddleware)

    # Global unhandled exception handler — never expose stack traces to clients.
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log.exception("unhandled_exception", path=str(request.url), error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Routers
    from app.routers.health import router as health_router
    from app.routers.admin import router as admin_router
    from app.routers.auth import router as auth_router
    from app.routers.deal_rooms import router as deal_rooms_router
    from app.routers.documents import router as documents_router
    from app.routers.jobs import router as jobs_router
    from app.routers.ml import router as ml_router
    from app.routers.reports import router as reports_router
    from app.routers.stream import router as stream_router
    from app.routers.annotations import _deal_room_router as annotations_dr_router
    from app.routers.annotations import _annotation_router as annotations_router
    from app.routers.management_qa import router as management_qa_router
    from app.routers.management_qa import _mq_router as management_question_router
    from app.routers.comparison import router as comparison_router
    from app.routers.invites import router as invites_router
    from app.routers.permissions import router as permissions_router
    app.include_router(health_router)
    app.include_router(admin_router)
    app.include_router(auth_router)
    app.include_router(invites_router)
    # comparison must come before deal_rooms so /compare and /search
    # are matched before the /{room_id} wildcard in deal_rooms
    app.include_router(comparison_router)
    app.include_router(deal_rooms_router)
    app.include_router(documents_router)
    app.include_router(jobs_router)
    app.include_router(ml_router)
    app.include_router(reports_router)
    app.include_router(stream_router)
    app.include_router(annotations_dr_router)
    app.include_router(annotations_router)
    app.include_router(management_qa_router)
    app.include_router(management_question_router)
    app.include_router(permissions_router)

    return app


app = create_app()
