"""ManagementQuestion repository."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.management_qa import ManagementQuestion


class ManagementQuestionRepository:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def bulk_insert(
        self, questions: list[dict[str, Any]]
    ) -> list[ManagementQuestion]:
        """Insert a batch of ManagementQuestion records and return them."""
        objects = [
            ManagementQuestion(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                deal_room_id=q["deal_room_id"],
                report_id=q["report_id"],
                source_item_id=q.get("source_item_id"),
                category=q["category"],
                question=q["question"],
                priority=q["priority"],
            )
            for q in questions
        ]
        self.session.add_all(objects)
        await self.session.flush()
        for obj in objects:
            await self.session.refresh(obj)
        return objects

    async def list_by_report_grouped(
        self, report_id: uuid.UUID
    ) -> dict[str, list[ManagementQuestion]]:
        """Return questions keyed by category string."""
        result = await self.session.execute(
            select(ManagementQuestion)
            .where(
                ManagementQuestion.report_id == report_id,
                ManagementQuestion.tenant_id == self.tenant_id,
            )
            .order_by(ManagementQuestion.category, ManagementQuestion.created_at)
        )
        rows = result.scalars().all()
        grouped: dict[str, list[ManagementQuestion]] = {}
        for q in rows:
            grouped.setdefault(q.category, []).append(q)
        return grouped

    async def list_by_report(
        self,
        report_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
    ) -> tuple[list[ManagementQuestion], int]:
        from sqlalchemy import func

        base_q = select(ManagementQuestion).where(
            ManagementQuestion.report_id == report_id,
            ManagementQuestion.tenant_id == self.tenant_id,
        )
        if category is not None:
            base_q = base_q.where(ManagementQuestion.category == category)

        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await self.session.execute(count_q)).scalar_one()

        rows = (
            await self.session.execute(
                base_q
                .order_by(ManagementQuestion.category, ManagementQuestion.created_at)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return list(rows), total

    async def get_by_id(self, question_id: uuid.UUID) -> ManagementQuestion | None:
        result = await self.session.execute(
            select(ManagementQuestion).where(
                ManagementQuestion.id == question_id,
                ManagementQuestion.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def record_answer(
        self,
        question_id: uuid.UUID,
        answer_notes: str,
        answered_by: uuid.UUID,
    ) -> ManagementQuestion | None:
        q = await self.get_by_id(question_id)
        if q is None:
            return None
        q.answered = True
        q.answer_notes = answer_notes
        q.answered_by = answered_by
        q.answered_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(q)
        return q
