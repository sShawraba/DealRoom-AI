"""Add role column to document_permissions for role-based permission grants.

Revision ID: 006
Revises: 005
Create Date: 2026-06-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_permissions",
        sa.Column("role", sa.String(50), nullable=True),
    )
    bind = op.get_bind()
    has_uq = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname = 'uq_doc_permission' AND conrelid = 'document_permissions'::regclass"
        )
    ).scalar()
    if has_uq:
        op.drop_constraint("uq_doc_permission", "document_permissions", type_="unique")


def downgrade() -> None:
    op.drop_column("document_permissions", "role")
