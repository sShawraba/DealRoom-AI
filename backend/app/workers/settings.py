import sys

# Patch pydantic v1's ForwardRef resolver for Python 3.12+.
# In 3.12, ForwardRef._evaluate() requires recursive_guard as a keyword argument.
# langsmith still ships pydantic v1 schemas (List[Run]), which crash at import time
# of langchain_openai unless we fix this first.
if sys.version_info >= (3, 12):
    try:
        import typing as _typing
        from pydantic import v1 as _pydantic_v1

        _orig_evaluate = getattr(_pydantic_v1.typing, "evaluate_forwardref", None)

        def _patched_evaluate_forwardref(type_: _typing.ForwardRef, globalns, localns):
            return type_._evaluate(globalns, localns, recursive_guard=frozenset())

        _pydantic_v1.typing.evaluate_forwardref = _patched_evaluate_forwardref
    except Exception:
        pass

import structlog
from arq.connections import RedisSettings

from app.core.config import settings

log = structlog.get_logger(__name__)


def _redis_settings() -> RedisSettings:
    import urllib.parse
    url = settings.redis_url or "redis://redis:6379/0"
    parsed = urllib.parse.urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "redis",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
    )


from app.workers.tasks import task_ingest_document, task_run_analysis  # noqa: E402


async def startup(ctx: dict) -> None:
    """Load Vault secrets and initialise DB/Redis/MinIO before any job runs."""
    from app.core.vault import load_all_secrets
    from app.core.database import init_db
    from app.core.redis import init_redis
    from app.core.minio import init_minio
    from app.core.logging import setup_logging

    try:
        secrets = load_all_secrets()
        for key, value in secrets.items():
            setattr(settings, key, value)
        log.info("vault.secrets_loaded", vault=settings.VAULT_ADDR)
    except Exception as exc:
        raise RuntimeError(f"Worker cannot reach Vault at {settings.VAULT_ADDR}: {exc}") from exc

    setup_logging()
    init_db(settings.database_url)
    init_redis(settings.redis_url)
    init_minio()
    log.info("worker.startup_complete")


async def shutdown(ctx: dict) -> None:
    """Called by ARQ after the current job finishes on SIGTERM — exits cleanly."""
    from app.core.database import dispose_db
    from app.core.redis import dispose_redis
    await dispose_db()
    await dispose_redis()
    log.info("worker.shutdown", message="Draining and exiting cleanly")


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [task_ingest_document, task_run_analysis]
    redis_settings = _redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10            # concurrent async jobs per worker process
    max_tries = 3
    job_timeout = 300       # seconds
    keep_result = 3600      # keep job result for 1 hour
