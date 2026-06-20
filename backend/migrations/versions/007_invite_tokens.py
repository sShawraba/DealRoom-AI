"""Add invite_tokens table for email-based user invitations.

Revision ID: 007
Revises: 006
Create Date: 2026-06-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invite_tokens",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invited_by_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("deal_room_id", sa.UUID(as_uuid=True), sa.ForeignKey("deal_rooms.id", ondelete="CASCADE"), nullable=True),
        sa.Column("deal_room_role", sa.String(50), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_invite_tokens_token", "invite_tokens", ["token"], unique=True)
    op.create_index("ix_invite_tokens_email", "invite_tokens", ["email"])


def downgrade() -> None:
    op.drop_index("ix_invite_tokens_email", "invite_tokens")
    op.drop_index("ix_invite_tokens_token", "invite_tokens")
    op.drop_table("invite_tokens")
