"""ManagementQuestion model for Q&A generated from report findings."""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from app.core.database import Base

qa_category_pg = PgEnum(
    "financial", "legal", "operational", "strategic",
    name="qa_category",
    create_type=False,
)

qa_priority_pg = PgEnum(
    "critical", "high", "medium",
    name="qa_priority",
    create_type=False,
)


class ManagementQuestion(Base):
    __tablename__ = "management_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    deal_room_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("deal_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_item_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("report_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(qa_category_pg, nullable=False)
    question: Mapped[str] = mapped_column(sa.Text, nullable=False)
    priority: Mapped[str] = mapped_column(qa_priority_pg, nullable=False)
    answered: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default="false"
    )
    answer_notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    answered_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
    )
    answered_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
