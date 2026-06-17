"""Auth, tenancy, and access control tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, INET, UUID, ENUM as PG_ENUM
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENUMs ─────────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'viewer')")
    op.execute(
        "CREATE TYPE deal_room_role AS ENUM ('owner', 'senior_analyst', 'analyst', 'viewer')"
    )
    op.execute("CREATE TYPE deal_status AS ENUM ('active', 'archived', 'closed')")
    op.execute(
        "CREATE TYPE risk_tier AS ENUM ('low', 'medium', 'high', 'critical')"
    )

    # ── updated_at trigger function ───────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ── tenants ───────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute("""
        CREATE TRIGGER trg_tenants_updated_at
        BEFORE UPDATE ON tenants
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", PG_ENUM("admin", "analyst", "viewer", name="user_role", create_type=False), nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.execute("""
        CREATE TRIGGER trg_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)

    # ── deal_rooms ────────────────────────────────────────────────────────────
    op.create_table(
        "deal_rooms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_company", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", PG_ENUM("active", "archived", "closed", name="deal_status", create_type=False), nullable=False, server_default="active"),
        sa.Column("risk_tier", sa.String(50), nullable=True),
        sa.Column("risk_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deal_rooms_tenant_id", "deal_rooms", ["tenant_id"])
    op.execute("""
        CREATE TRIGGER trg_deal_rooms_updated_at
        BEFORE UPDATE ON deal_rooms
        FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)

    # ── deal_room_members ─────────────────────────────────────────────────────
    op.create_table(
        "deal_room_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deal_room_id", UUID(as_uuid=True), sa.ForeignKey("deal_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", PG_ENUM("owner", "senior_analyst", "analyst", "viewer", name="deal_room_role", create_type=False), nullable=False, server_default="analyst"),
        sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("deal_room_id", "user_id", name="uq_deal_room_member"),
    )
    op.create_index("ix_drm_tenant_id", "deal_room_members", ["tenant_id"])
    op.create_index("ix_drm_deal_room_id", "deal_room_members", ["deal_room_id"])
    op.create_index("ix_drm_user_id", "deal_room_members", ["user_id"])

    # ── document_permissions (stub) ───────────────────────────────────────────
    op.create_table(
        "document_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("can_view", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("can_download", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("granted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "user_id", name="uq_doc_permission"),
    )
    op.create_index("ix_doc_perm_tenant_id", "document_permissions", ["tenant_id"])
    op.create_index("ix_doc_perm_document_id", "document_permissions", ["document_id"])

    # ── audit_log ─────────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_room_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=False),
        sa.Column("actor_email", sa.String(255), nullable=False),
        sa.Column("actor_role", sa.String(50), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("resource_name", sa.String(255), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("ip_address", INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])
    op.create_index("ix_audit_log_tenant_deal", "audit_log", ["tenant_id", "deal_room_id"])
    op.create_index("ix_audit_log_occurred_at", "audit_log", ["occurred_at"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])

    # audit_log is append-only: block DELETE and UPDATE via trigger.
    # (REVOKE FROM PUBLIC cannot remove owner privileges, so a trigger enforces immutability.)
    op.execute("REVOKE DELETE, UPDATE ON audit_log FROM PUBLIC")
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_log_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is immutable: DELETE and UPDATE are not permitted'
                USING ERRCODE = '42501';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_audit_log_immutable
        BEFORE DELETE OR UPDATE ON audit_log
        FOR EACH STATEMENT EXECUTE FUNCTION audit_log_immutable()
    """)


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("document_permissions")
    op.drop_table("deal_room_members")
    op.drop_table("deal_rooms")
    op.drop_table("users")
    op.drop_table("tenants")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at CASCADE")
    op.execute("DROP TYPE IF EXISTS risk_tier")
    op.execute("DROP TYPE IF EXISTS deal_status")
    op.execute("DROP TYPE IF EXISTS deal_room_role")
    op.execute("DROP TYPE IF EXISTS user_role")
