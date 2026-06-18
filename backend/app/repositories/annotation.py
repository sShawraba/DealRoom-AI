"""Annotation and AnnotationReply repositories."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import Annotation, AnnotationReply
from app.models.report import Report, ReportItem


class AnnotationRepository:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def _assert_report_not_approved(self, report_item_id: uuid.UUID) -> None:
        """Raise 409 if the report owning this item is approved."""
        result = await self.session.execute(
            select(Report.status)
            .join(ReportItem, ReportItem.report_id == Report.id)
            .where(ReportItem.id == report_item_id)
        )
        status = result.scalar_one_or_none()
        if status == "approved":
            raise HTTPException(409, "Report is approved and read-only")

    async def create(
        self,
        deal_room_id: uuid.UUID,
        report_item_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
        annotation_type: str = "comment",
    ) -> Annotation:
        await self._assert_report_not_approved(report_item_id)
        annotation = Annotation(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            deal_room_id=deal_room_id,
            report_item_id=report_item_id,
            author_id=author_id,
            content=content,
            type=annotation_type,
        )
        self.session.add(annotation)
        await self.session.flush()
        await self.session.refresh(annotation)
        return annotation

    async def get_by_id(self, annotation_id: uuid.UUID) -> Annotation | None:
        result = await self.session.execute(
            select(Annotation).where(
                Annotation.id == annotation_id,
                Annotation.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_deal_room(
        self,
        deal_room_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[dict[str, list[Annotation]], int]:
        """Return annotations keyed by report_item_id (as str), paginated."""
        base_q = (
            select(Annotation)
            .where(
                Annotation.deal_room_id == deal_room_id,
                Annotation.tenant_id == self.tenant_id,
            )
            .order_by(Annotation.created_at)
        )
        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await self.session.execute(count_q)).scalar_one()

        rows = (
            await self.session.execute(
                base_q.offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()

        grouped: dict[str, list[Annotation]] = {}
        for ann in rows:
            key = str(ann.report_item_id)
            grouped.setdefault(key, []).append(ann)
        return grouped, total

    async def resolve(
        self,
        annotation_id: uuid.UUID,
        resolved_by: uuid.UUID,
        new_type: str | None = None,
    ) -> Annotation | None:
        annotation = await self.get_by_id(annotation_id)
        if annotation is None:
            return None
        annotation.resolved = True
        annotation.resolved_by = resolved_by
        annotation.resolved_at = datetime.now(timezone.utc)
        if new_type is not None:
            annotation.type = new_type
        await self.session.flush()
        await self.session.refresh(annotation)
        return annotation

    async def patch(
        self, annotation_id: uuid.UUID, **kwargs: Any
    ) -> Annotation | None:
        annotation = await self.get_by_id(annotation_id)
        if annotation is None:
            return None
        for key, value in kwargs.items():
            setattr(annotation, key, value)
        await self.session.flush()
        await self.session.refresh(annotation)
        return annotation

    async def get_unresolved_disputed_count(self, report_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(Annotation.id))
            .join(ReportItem, ReportItem.id == Annotation.report_item_id)
            .where(
                ReportItem.report_id == report_id,
                Annotation.type == "disputed",
                Annotation.resolved == False,  # noqa: E712
            )
        )
        return result.scalar_one()

    async def create_reply(
        self,
        annotation_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
    ) -> AnnotationReply:
        reply = AnnotationReply(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            annotation_id=annotation_id,
            author_id=author_id,
            content=content,
        )
        self.session.add(reply)
        await self.session.flush()
        await self.session.refresh(reply)
        return reply

    async def list_replies(self, annotation_id: uuid.UUID) -> list[AnnotationReply]:
        result = await self.session.execute(
            select(AnnotationReply)
            .where(
                AnnotationReply.annotation_id == annotation_id,
                AnnotationReply.tenant_id == self.tenant_id,
            )
            .order_by(AnnotationReply.created_at)
        )
        return list(result.scalars().all())
