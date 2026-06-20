"""Convert report_items.citation from JSON to JSONB for asyncpg compatibility

Revision ID: 008_citation_jsonb
Revises: 007_invite_tokens
Create Date: 2026-06-20
"""
from alembic import op

revision = "008_citation_jsonb"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE report_items ALTER COLUMN citation TYPE JSONB USING citation::JSONB"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE report_items ALTER COLUMN citation TYPE JSON USING citation::JSON"
    )
