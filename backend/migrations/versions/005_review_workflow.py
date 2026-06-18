"""005_review_workflow

Add annotation_type, qa_category, qa_priority ENUMs.
Extend report_status with in_review + approved values.
Add edited_content/edited_by/edited_at to report_items.
Create annotations, annotation_replies, report_approvals, management_questions tables.

Revision ID: 005
Revises: 004b
Create Date: 2026-06-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

revision = "005"
down_revision = "004b"
branch_labels = None
depends_on = None

annotation_type = PgEnum(
    "comment", "verified", "disputed",
    name="annotation_type",
    create_type=True,
)
qa_category = PgEnum(
    "financial", "legal", "operational", "strategic",
    name="qa_category",
    create_type=True,
)
qa_priority = PgEnum(
    "critical", "high", "medium",
    name="qa_priority",
    create_type=True,
)


def upgrade() -> None:
    bind = op.get_bind()

    # Extend report_status enum with new workflow values
    bind.execute(sa.text("ALTER TYPE report_status ADD VALUE IF NOT EXISTS 'in_review'"))
    bind.execute(sa.text("ALTER TYPE report_status ADD VALUE IF NOT EXISTS 'approved'"))

    # Add edit-tracking columns to report_items
    op.add_column("report_items", sa.Column("edited_content", sa.Text, nullable=True))
    op.add_column(
        "report_items",
        sa.Column(
            "edited_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "report_items",
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create new ENUM types
    annotation_type.create(bind, checkfirst=True)
    qa_category.create(bind, checkfirst=True)
    qa_priority.create(bind, checkfirst=True)

    op.create_table(
        "annotations",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deal_room_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("deal_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_item_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("report_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "type",
            PgEnum("comment", "verified", "disputed", name="annotation_type", create_type=False),
            nullable=False,
            server_default="comment",
        ),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "resolved_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_annotations_report_item_id", "annotations", ["report_item_id"])
    op.create_index("ix_annotations_type_resolved", "annotations", ["type", "resolved"])
    op.create_index("ix_annotations_deal_room_id", "annotations", ["deal_room_id"])

    op.create_table(
        "annotation_replies",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "annotation_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("annotations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_annotation_replies_annotation_id", "annotation_replies", ["annotation_id"])

    op.create_table(
        "report_approvals",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "approved_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("sign_off_notes", sa.Text, nullable=True),
        sa.Column("disputed_resolved_count", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "management_questions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deal_room_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("deal_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_item_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("report_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "category",
            PgEnum("financial", "legal", "operational", "strategic", name="qa_category", create_type=False),
            nullable=False,
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column(
            "priority",
            PgEnum("critical", "high", "medium", name="qa_priority", create_type=False),
            nullable=False,
        ),
        sa.Column("answered", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("answer_notes", sa.Text, nullable=True),
        sa.Column(
            "answered_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_management_questions_report_id", "management_questions", ["report_id"])
    op.create_index("ix_management_questions_deal_room_id", "management_questions", ["deal_room_id"])


def downgrade() -> None:
    op.drop_index("ix_management_questions_deal_room_id", table_name="management_questions")
    op.drop_index("ix_management_questions_report_id", table_name="management_questions")
    op.drop_table("management_questions")
    op.drop_table("report_approvals")
    op.drop_index("ix_annotation_replies_annotation_id", table_name="annotation_replies")
    op.drop_table("annotation_replies")
    op.drop_index("ix_annotations_deal_room_id", table_name="annotations")
    op.drop_index("ix_annotations_type_resolved", table_name="annotations")
    op.drop_index("ix_annotations_report_item_id", table_name="annotations")
    op.drop_table("annotations")

    bind = op.get_bind()
    qa_priority.drop(bind, checkfirst=True)
    qa_category.drop(bind, checkfirst=True)
    annotation_type.drop(bind, checkfirst=True)

    op.drop_column("report_items", "edited_at")
    op.drop_column("report_items", "edited_by")
    op.drop_column("report_items", "edited_content")
