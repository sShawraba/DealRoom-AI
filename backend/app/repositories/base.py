from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseTenantRepository(Generic[ModelType]):
    """
    Base repository for all tenant-scoped models.

    Every query automatically filters by tenant_id so cross-tenant data
    leakage is impossible at the repository layer.
    """

    model: type[ModelType]

    def __init__(self, session: AsyncSession, tenant_id: UUID, user_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id

    def _base_query(self):
        """Return a SELECT already filtered by tenant_id. Subclasses may override."""
        return select(self.model).where(self.model.tenant_id == self.tenant_id)

    async def get_by_id(self, id: UUID) -> ModelType | None:
        result = await self.session.execute(
            self._base_query().where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        **filters: Any,
    ) -> tuple[list[ModelType], int]:
        """Return (items, total_count) for the given page."""
        base = self._base_query()
        for attr, value in filters.items():
            base = base.where(getattr(self.model, attr) == value)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_q)).scalar_one()

        items_q = base.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(items_q)).scalars().all()
        return list(rows), total

    async def create(self, **kwargs: Any) -> ModelType:
        obj = self.model(tenant_id=self.tenant_id, **kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, id: UUID, **kwargs: Any) -> ModelType | None:
        obj = await self.get_by_id(id)
        if obj is None:
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id: UUID) -> bool:
        obj = await self.get_by_id(id)
        if obj is None:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True
