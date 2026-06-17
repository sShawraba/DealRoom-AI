"""Document and DocumentChunk models for the ingestion pipeline."""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, document_status_enum, doc_type_enum


class Document(Base, TimestampMixin):
    """Represents an uploaded file in a deal room. Content lives in MinIO."""

    __tablename__ = "documents"

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
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    minio_key: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    doc_type: Mapped[str] = mapped_column(
        doc_type_enum, nullable=False, server_default="other"
    )
    status: Mapped[str] = mapped_column(
        document_status_enum, nullable=False, server_default="uploaded"
    )
    page_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    arq_job_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)


class DocumentChunk(Base):
    """A chunk of parsed text/table content from a document, with its embedding."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), nullable=False
    )
    deal_room_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    content_type: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, server_default="prose"
    )
    page_number: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    section_header: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    embedding: Mapped[list | None] = mapped_column(Vector(1536), nullable=True)
    token_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    is_suspicious: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default="false"
    )
    pii_types_found: Mapped[list] = mapped_column(
        sa.JSON, nullable=False, server_default="[]"
    )
    # Parent-child chunking (added Phase 5)
    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_level: Mapped[str] = mapped_column(
        sa.String(10), nullable=False, server_default="parent"
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
