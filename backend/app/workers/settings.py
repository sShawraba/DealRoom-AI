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


async def shutdown(ctx: dict) -> None:
    """Called by ARQ after the current job finishes on SIGTERM — exits cleanly."""
    log.info("worker.shutdown", message="Draining and exiting cleanly")


class WorkerSettings:
    """ARQ worker configuration.

    ARQ handles SIGTERM natively: it finishes the running job before exiting.
    The on_shutdown hook logs a message so operators can confirm clean draining
    in container logs before the process exits.
    """

    functions = [task_ingest_document, task_run_analysis]
    redis_settings = _redis_settings()
    on_shutdown = shutdown
    max_tries = 3
    job_timeout = 300       # seconds
    keep_result = 3600      # keep job result for 1 hour
