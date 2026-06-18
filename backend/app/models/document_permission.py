"""DocumentPermission — per-user or per-role access grants for a document."""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentPermission(Base):
    __tablename__ = "document_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    role: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    can_view: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    can_download: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
