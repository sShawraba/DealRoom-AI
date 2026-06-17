import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    """Append-only audit trail. The app DB user has no DELETE or UPDATE on this table."""

    __tablename__ = "audit_log"
    __table_args__ = (
        sa.Index("ix_audit_log_tenant_deal", "tenant_id", "deal_room_id"),
        sa.Index("ix_audit_log_occurred_at", "occurred_at", postgresql_ops={"occurred_at": "DESC"}),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), nullable=False, index=True
    )
    deal_room_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), nullable=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), nullable=False
    )
    actor_email: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    actor_role: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    action: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), nullable=True
    )
    resource_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
