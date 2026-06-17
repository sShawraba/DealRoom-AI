"""Documents and document_chunks tables with pgvector HNSW index

Revision ID: 003
Revises: 002
Create Date: 2026-06-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM as PG_ENUM
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENUMs ─────────────────────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE document_status AS ENUM "
        "('uploaded', 'processing', 'indexed', 'failed')"
    )
    op.execute(
        "CREATE TYPE doc_type AS ENUM "
        "('financial_statement', 'legal_contract', 'market_report', "
        "'management_presentation', 'other')"
    )

    # ── documents ─────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deal_room_id",
            UUID(as_uuid=True),
            sa.ForeignKey("deal_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("minio_key", sa.String(1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column(
            "doc_type",
            PG_ENUM(
                "financial_statement",
                "legal_contract",
                "market_report",
                "management_presentation",
                "other",
                name="doc_type",
                create_type=False,
            ),
            nullable=False,
            server_default="other",
        ),
        sa.Column(
            "status",
            PG_ENUM(
                "uploaded",
                "processing",
                "indexed",
                "failed",
                name="document_status",
                create_type=False,
            ),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("arq_job_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_documents_tenant_deal", "documents", ["tenant_id", "deal_room_id"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.execute("""
        CREATE TRIGGER trg_documents_updated_at
        BEFORE UPDATE ON documents
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)

    # ── Add FK from document_permissions → documents ──────────────────────────
    # Phase 1 created document_permissions with document_id as plain UUID (no FK).
    # Now that documents table exists we add the FK constraint.
    op.create_foreign_key(
        "fk_doc_perm_document_id",
        "document_permissions",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ── document_chunks ───────────────────────────────────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_room_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "content_type", sa.String(20), nullable=False, server_default="prose"
        ),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("section_header", sa.String(512), nullable=True),
        # pgvector column — created with raw SQL so we can use the vector type
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("is_suspicious", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("pii_types_found", sa.JSON, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Add the vector column after table creation (requires pgvector extension from 001)
    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)"
    )
    # HNSW index for cosine similarity search
    op.execute(
        "CREATE INDEX idx_chunks_embedding ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)"
    )
    op.create_index(
        "ix_chunks_tenant_deal", "document_chunks", ["tenant_id", "deal_room_id"]
    )
    op.create_index("ix_chunks_document_id", "document_chunks", ["document_id"])


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_constraint(
        "fk_doc_perm_document_id", "document_permissions", type_="foreignkey"
    )
    op.drop_table("documents")
    op.execute("DROP TYPE IF EXISTS document_status")
    op.execute("DROP TYPE IF EXISTS doc_type")
