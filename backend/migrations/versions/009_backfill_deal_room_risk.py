"""Backfill deal_room risk_score and risk_tier from latest report

Revision ID: 009_backfill_deal_room_risk
Revises: 008_citation_jsonb
Create Date: 2026-06-20
"""
from alembic import op

revision = "009_backfill_deal_room_risk"
down_revision = "008_citation_jsonb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE deal_rooms dr
        SET
            risk_score = r.risk_score,
            risk_tier  = r.risk_tier
        FROM (
            SELECT DISTINCT ON (deal_room_id)
                deal_room_id,
                risk_score,
                risk_tier
            FROM reports
            WHERE risk_score IS NOT NULL
            ORDER BY deal_room_id, created_at DESC
        ) r
        WHERE dr.id = r.deal_room_id
          AND dr.risk_score IS NULL
    """)


def downgrade() -> None:
    pass
