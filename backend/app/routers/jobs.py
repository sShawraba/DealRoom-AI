"""ARQ job status endpoint."""
from __future__ import annotations

import structlog
from arq.jobs import JobStatus
from fastapi import APIRouter

from app.core.deps import CurrentUserDep
from app.core.redis import get_arq_pool
from app.schemas.document import JobStatusResponse

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: CurrentUserDep,
) -> JobStatusResponse:
    """
    Return the current status of an ARQ background job.

    Status values: queued | in_progress | complete | failed | not_found
    """
    arq = await get_arq_pool()
    job = arq.job(job_id)

    try:
        raw_status = await job.status()
    except Exception:
        return JobStatusResponse(job_id=job_id, status="not_found")

    status_map = {
        JobStatus.queued: "queued",
        JobStatus.in_progress: "in_progress",
        JobStatus.complete: "complete",
        JobStatus.not_found: "not_found",
        JobStatus.deferred: "queued",
        JobStatus.expired: "failed",
        JobStatus.aborting: "in_progress",
        JobStatus.aborted: "failed",
    }
    status_str = status_map.get(raw_status, str(raw_status))

    error: str | None = None
    if raw_status == JobStatus.complete:
        try:
            result = await job.result(timeout=0)
            if isinstance(result, Exception):
                error = str(result)
                status_str = "failed"
        except Exception:
            pass

    return JobStatusResponse(job_id=job_id, status=status_str, error=error)
