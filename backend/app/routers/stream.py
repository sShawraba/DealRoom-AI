"""SSE streaming endpoint — streams analysis events from Redis pub/sub."""
from __future__ import annotations

import json
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.core.deps import CurrentUserDep, SessionDep, get_current_user
from app.core.redis import get_redis
from app.repositories.deal_room import DealRoomRepository
from app.services.streaming import AnalysisEvent

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/deal-rooms/{deal_room_id}/reports/{report_id}",
    tags=["stream"],
)


@router.get("/stream")
async def stream_analysis(
    deal_room_id: UUID,
    report_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> EventSourceResponse:
    """Stream analysis progress events via SSE until completion or failure."""
    deal_room_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    deal_room = await deal_room_repo.get_by_id(deal_room_id)
    if deal_room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal room not found")

    redis = await get_redis()

    async def generator():
        pubsub = redis.pubsub()
        channel = f"report:{report_id}:events"
        await pubsub.subscribe(channel)
        log.info("stream.connected", report_id=str(report_id), user_id=str(current_user.id))
        try:
            yield {"data": json.dumps({"type": "connected", "report_id": str(report_id)})}
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                raw = message["data"]
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                data = json.loads(raw)
                yield {"data": json.dumps(data)}
                if data.get("type") in (AnalysisEvent.ANALYSIS_DONE, AnalysisEvent.ANALYSIS_FAILED):
                    break
        finally:
            await pubsub.unsubscribe(channel)
            log.info("stream.disconnected", report_id=str(report_id))

    return EventSourceResponse(generator())
