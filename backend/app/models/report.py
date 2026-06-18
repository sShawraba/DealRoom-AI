"""Report and ReportItem models for the synthesis pipeline."""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from app.core.database import Base
from app.models.base import TimestampMixin

report_status_enum = PgEnum(
    "pending", "running", "draft", "failed", "in_review", "approved",
    name="report_status",
    create_type=False,
)

section_type_enum = PgEnum(
    "executive_summary", "financial_health", "legal_flags",
    "commercial_assessment", "red_flags", "key_questions",
    name="section_type",
    create_type=False,
)


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

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
    created_by: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        report_status_enum, nullable=False, server_default="pending"
    )
    arq_job_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    risk_tier: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    risk_shap_factors: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    citation_coverage: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    has_unverified: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default="false"
    )
    missing_context: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)


class ReportItem(Base):
    __tablename__ = "report_items"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), nullable=False
    )
    section_type: Mapped[str] = mapped_column(section_type_enum, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    citation: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    is_verified: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default="true"
    )
    item_index: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    edited_content: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    edited_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
