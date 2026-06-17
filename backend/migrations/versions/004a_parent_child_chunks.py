"""004a_parent_child_chunks

Add parent_chunk_id and chunk_level columns to document_chunks for
parent-child chunking strategy (parent=512 tokens, child=128 tokens).

Revision ID: 004a
Revises: 003
Create Date: 2026-06-15
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "004a"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column(
            "parent_chunk_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("document_chunks.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "document_chunks",
        sa.Column(
            "chunk_level",
            sa.String(10),
            nullable=False,
            server_default="parent",
        ),
    )
    op.create_index(
        "ix_document_chunks_parent_chunk_id",
        "document_chunks",
        ["parent_chunk_id"],
    )
    op.create_index(
        "ix_document_chunks_chunk_level",
        "document_chunks",
        ["chunk_level"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_chunk_level", table_name="document_chunks")
    op.drop_index("ix_document_chunks_parent_chunk_id", table_name="document_chunks")
    op.drop_column("document_chunks", "chunk_level")
    op.drop_column("document_chunks", "parent_chunk_id")
