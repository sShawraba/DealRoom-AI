"""004b_reports

Create report_status and section_type ENUMs, reports and report_items tables.

Revision ID: 004b
Revises: 004a
Create Date: 2026-06-15
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

revision = "004b"
down_revision = "004a"
branch_labels = None
depends_on = None

report_status = PgEnum(
    "pending", "running", "draft", "failed",
    name="report_status",
    create_type=True,
)
section_type_enum = PgEnum(
    "executive_summary", "financial_health", "legal_flags",
    "commercial_assessment", "red_flags", "key_questions",
    name="section_type",
    create_type=True,
)


def upgrade() -> None:
    bind = op.get_bind()
    report_status.create(bind, checkfirst=True)
    section_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "reports",
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
            "created_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            PgEnum("pending", "running", "draft", "failed", name="report_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("arq_job_id", sa.String(255), nullable=True),
        sa.Column("risk_score", sa.Float, nullable=True),
        sa.Column("risk_tier", sa.String(20), nullable=True),
        sa.Column("risk_shap_factors", sa.JSON, nullable=True),
        sa.Column("citation_coverage", sa.Float, nullable=True),
        sa.Column("has_unverified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("missing_context", sa.JSON, nullable=True),
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
    op.create_index("ix_reports_deal_room_id", "reports", ["deal_room_id"])
    op.create_index("ix_reports_tenant_id", "reports", ["tenant_id"])

    op.create_table(
        "report_items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "section_type",
            PgEnum(
                "executive_summary", "financial_health", "legal_flags",
                "commercial_assessment", "red_flags", "key_questions",
                name="section_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("citation", sa.JSON, nullable=True),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("item_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_report_items_report_id", "report_items", ["report_id"])


def downgrade() -> None:
    op.drop_table("report_items")
    op.drop_index("ix_reports_tenant_id", table_name="reports")
    op.drop_index("ix_reports_deal_room_id", table_name="reports")
    op.drop_table("reports")
    bind = op.get_bind()
    section_type_enum.drop(bind, checkfirst=True)
    report_status.drop(bind, checkfirst=True)
