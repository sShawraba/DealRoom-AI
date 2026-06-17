"""Repositories for Report and ReportItem."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report, ReportItem
from app.repositories.base import BaseTenantRepository


class ReportRepository(BaseTenantRepository[Report]):
    model = Report

    def _base_query(self):
        return select(Report).where(Report.tenant_id == self.tenant_id)

    async def list_for_deal_room(
        self, deal_room_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Report], int]:
        return await self.list_all(page=page, page_size=page_size, deal_room_id=deal_room_id)

    async def get_with_items(self, report_id: uuid.UUID) -> Report | None:
        return await self.get_by_id(report_id)


class ReportItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_insert_items(
        self,
        report_id: uuid.UUID,
        tenant_id: uuid.UUID,
        sections: dict[str, list[Any]],
    ) -> None:
        """Insert all section items for a report in a single batch."""
        objects: list[ReportItem] = []
        for section_type, items in sections.items():
            for idx, item in enumerate(items):
                if isinstance(item, dict):
                    content = item.get("content", "")
                    citation = item.get("citation")
                    is_verified = item.get("is_verified", True)
                else:
                    content = getattr(item, "content", "")
                    citation = getattr(item, "citation", None)
                    is_verified = getattr(item, "is_verified", True)

                objects.append(
                    ReportItem(
                        id=uuid.uuid4(),
                        report_id=report_id,
                        tenant_id=tenant_id,
                        section_type=section_type,
                        content=content,
                        citation=citation,
                        is_verified=is_verified,
                        item_index=idx,
                    )
                )
        self.session.add_all(objects)
        await self.session.flush()

    async def get_items_for_report(self, report_id: uuid.UUID) -> list[ReportItem]:
        result = await self.session.execute(
            select(ReportItem)
            .where(ReportItem.report_id == report_id)
            .order_by(ReportItem.section_type, ReportItem.item_index)
        )
        return list(result.scalars().all())
