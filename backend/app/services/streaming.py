"""Streaming event publisher — publishes analysis progress to Redis pub/sub."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import structlog

from app.core.redis import get_redis

log = structlog.get_logger(__name__)


class AnalysisEvent:
    STARTED          = "analysis.started"
    RESEARCH_START   = "research.started"
    RESEARCH_DONE    = "research.complete"
    ML_SCORED        = "ml.scored"
    SYNTHESIS_START  = "synthesis.started"
    SECTION_COMPLETE = "synthesis.section_complete"
    ANALYSIS_DONE    = "analysis.complete"
    ANALYSIS_FAILED  = "analysis.failed"


async def publish_progress(report_id: UUID | str, event_type: str, **data) -> None:
    """Publish a JSON event to Redis channel `report:{report_id}:events`."""
    redis = await get_redis()
    payload = json.dumps(
        {
            "type": event_type,
            "report_id": str(report_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
    )
    channel = f"report:{report_id}:events"
    await redis.publish(channel, payload)
    log.info("stream.event", report_id=str(report_id), event_type=event_type)
