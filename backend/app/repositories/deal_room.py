from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, select

from app.models.deal_room import DealRoom
from app.models.deal_room_member import DealRoomMember
from app.repositories.base import BaseTenantRepository


class DealRoomRepository(BaseTenantRepository[DealRoom]):
    model = DealRoom

    def _base_query(self):
        """
        Only return deal rooms where the current user is an explicit member.
        Non-members see 0 results (404), never a 403.
        """
        return (
            select(DealRoom)
            .join(
                DealRoomMember,
                and_(
                    DealRoomMember.deal_room_id == DealRoom.id,
                    DealRoomMember.user_id == self.user_id,
                    DealRoomMember.tenant_id == self.tenant_id,
                ),
            )
            .where(DealRoom.tenant_id == self.tenant_id)
        )

    async def get_user_role(
        self, deal_room_id: UUID, user_id: UUID
    ) -> str | None:
        """Return the user's deal_room_role for this room, or None if not a member."""
        result = await self.session.execute(
            select(DealRoomMember.role).where(
                DealRoomMember.deal_room_id == deal_room_id,
                DealRoomMember.user_id == user_id,
                DealRoomMember.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_member(
        self,
        deal_room_id: UUID,
        user_id: UUID,
        role: str,
        invited_by: UUID | None = None,
    ) -> DealRoomMember:
        member = DealRoomMember(
            tenant_id=self.tenant_id,
            deal_room_id=deal_room_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
        )
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def remove_member(self, deal_room_id: UUID, user_id: UUID) -> bool:
        result = await self.session.execute(
            select(DealRoomMember).where(
                DealRoomMember.deal_room_id == deal_room_id,
                DealRoomMember.user_id == user_id,
                DealRoomMember.tenant_id == self.tenant_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            return False
        await self.session.delete(member)
        await self.session.flush()
        return True

    async def update_member_role(
        self, deal_room_id: UUID, user_id: UUID, role: str
    ) -> DealRoomMember | None:
        result = await self.session.execute(
            select(DealRoomMember).where(
                DealRoomMember.deal_room_id == deal_room_id,
                DealRoomMember.user_id == user_id,
                DealRoomMember.tenant_id == self.tenant_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            return None
        member.role = role
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def list_members(self, deal_room_id: UUID) -> list[DealRoomMember]:
        result = await self.session.execute(
            select(DealRoomMember).where(
                DealRoomMember.deal_room_id == deal_room_id,
                DealRoomMember.tenant_id == self.tenant_id,
            )
        )
        return list(result.scalars().all())
