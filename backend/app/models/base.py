from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Enum
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

# ── Re-export Base from database module for backwards compat ──────────────────
from app.core.database import Base  # noqa: F401

# ── ENUM type definitions (shared across models) ──────────────────────────────
# create_type=False: migrations own type creation, not SQLAlchemy metadata events.
user_role_enum = Enum(
    "admin", "analyst", "viewer",
    name="user_role",
    create_type=False,
)

deal_room_role_enum = Enum(
    "owner", "senior_analyst", "analyst", "viewer",
    name="deal_room_role",
    create_type=False,
)

deal_status_enum = Enum(
    "active", "archived", "closed",
    name="deal_status",
    create_type=False,
)

risk_tier_enum = Enum(
    "low", "medium", "high", "critical",
    name="risk_tier",
    create_type=False,
)

document_status_enum = Enum(
    "uploaded", "processing", "indexed", "failed",
    name="document_status",
    create_type=False,
)

doc_type_enum = Enum(
    "financial_statement", "legal_contract", "market_report",
    "management_presentation", "other",
    name="doc_type",
    create_type=False,
)

annotation_type_enum = Enum(
    "comment", "verified", "disputed",
    name="annotation_type",
    create_type=False,
)

qa_category_enum = Enum(
    "financial", "legal", "operational", "strategic",
    name="qa_category",
    create_type=False,
)

qa_priority_enum = Enum(
    "critical", "high", "medium",
    name="qa_priority",
    create_type=False,
)


# ── Mixin ─────────────────────────────────────────────────────────────────────
class TimestampMixin:
    """Adds created_at / updated_at columns. updated_at is managed by a DB trigger."""

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
