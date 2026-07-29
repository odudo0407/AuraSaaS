"""initial_schema — baseline migration compatible with SQLite and PostgreSQL.

Revision ID: 907656cdedac
Revises:
Create Date: 2026-06-08 19:51:29.466850

This migration creates all tables from the SQLAlchemy metadata.  It is
idempotent: if tables already exist (e.g. created by Base.metadata.create_all()
in ensure_demo_schema) the DDL is skipped.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision: str = "907656cdedac"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    """Check if a table already exists in the current connection."""
    insp = inspect(op.get_bind())
    return name in insp.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()

    # ── users ──
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("username", sa.String(length=100), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("avatar_url", sa.String(length=500), server_default="", nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("username"),
        )

    # ── stores ──
    if not _table_exists("stores"):
        op.create_table(
            "stores",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("city", sa.String(length=100), nullable=False),
            sa.Column("area", sa.String(length=200), server_default="", nullable=False),
            sa.Column("manager_name", sa.String(length=100), server_default="", nullable=False),
            sa.Column("status", sa.String(length=50), server_default="open", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── staff ──
    if not _table_exists("staff"):
        op.create_table(
            "staff",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("phone", sa.String(length=30), server_default="", nullable=False),
            sa.Column("role", sa.String(length=100), server_default="", nullable=False),
            sa.Column("salary", sa.Float(), server_default="0", nullable=False),
            sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── business_metrics_daily ──
    if not _table_exists("business_metrics_daily"):
        op.create_table(
            "business_metrics_daily",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("revenue", sa.Float(), server_default="0", nullable=False),
            sa.Column("total_revenue", sa.Float(), server_default="0", nullable=False),
            sa.Column("order_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("avg_ticket", sa.Float(), server_default="0", nullable=False),
            sa.Column("gross_margin", sa.Float(), server_default="0", nullable=False),
            sa.Column("refund_rate", sa.Float(), server_default="0", nullable=False),
            sa.Column("net_profit", sa.Float(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_metrics_store_date", "business_metrics_daily", ["store_id", "date"])

    # ── sku_performance ──
    if not _table_exists("sku_performance"):
        op.create_table(
            "sku_performance",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("sku_name", sa.String(length=200), nullable=False),
            sa.Column("category", sa.String(length=100), server_default="", nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("cost", sa.Float(), server_default="0", nullable=False),
            sa.Column("sales_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("sales_volume", sa.Integer(), server_default="0", nullable=False),
            sa.Column("revenue", sa.Float(), server_default="0", nullable=False),
            sa.Column("gross_margin", sa.Float(), server_default="0", nullable=False),
            sa.Column("refund_rate", sa.Float(), server_default="0", nullable=False),
            sa.Column("image_url", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_sku_store_date", "sku_performance", ["store_id", "date"])

    # ── external_factors ──
    if not _table_exists("external_factors"):
        op.create_table(
            "external_factors",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("weather", sa.String(length=100), server_default="", nullable=False),
            sa.Column("holiday", sa.String(length=100), server_default="", nullable=False),
            sa.Column("event", sa.String(length=200), server_default="", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_external_store_date", "external_factors", ["store_id", "date"])

    # ── knowledge_documents ──
    if not _table_exists("knowledge_documents"):
        op.create_table(
            "knowledge_documents",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("title", sa.String(length=300), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source", sa.String(length=500), server_default="", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── tenant_knowledge_documents ──
    if not _table_exists("tenant_knowledge_documents"):
        op.create_table(
            "tenant_knowledge_documents",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=300), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("file_type", sa.String(length=20), server_default="", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── agent_memories ──
    if not _table_exists("agent_memories"):
        op.create_table(
            "agent_memories",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=False),
            sa.Column("memory_type", sa.String(length=50), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── agent_traces ──
    if not _table_exists("agent_traces"):
        op.create_table(
            "agent_traces",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("trace_id", sa.String(length=36), nullable=False),
            sa.Column("user_query", sa.Text(), nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=50), server_default="running", nullable=False),
            sa.Column("steps_json", sa.Text(), nullable=False),
            sa.Column("final_answer", sa.Text(), server_default="", nullable=False),
            sa.Column("graph_state", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("trace_id"),
        )

    # ── agent_approvals ──
    if not _table_exists("agent_approvals"):
        op.create_table(
            "agent_approvals",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("session_id", sa.String(length=100), nullable=False),
            sa.Column("trace_id", sa.String(length=36), nullable=False),
            sa.Column("node_name", sa.String(length=100), server_default="", nullable=False),
            sa.Column("proposal", sa.Text(), nullable=False),
            sa.Column("estimated_cost", sa.Float(), server_default="0", nullable=False),
            sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
            sa.Column("reviewer_comment", sa.Text(), server_default="", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── marketing_campaigns ──
    if not _table_exists("marketing_campaigns"):
        op.create_table(
            "marketing_campaigns",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=300), nullable=False),
            sa.Column("description", sa.Text(), server_default="", nullable=False),
            sa.Column("budget", sa.Float(), server_default="0", nullable=False),
            sa.Column("status", sa.String(length=50), server_default="draft", nullable=False),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── campaign_results ──
    if not _table_exists("campaign_results"):
        op.create_table(
            "campaign_results",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("campaign_id", sa.Integer(), nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=False),
            sa.Column("orders_before", sa.Integer(), server_default="0", nullable=False),
            sa.Column("orders_after", sa.Integer(), server_default="0", nullable=False),
            sa.Column("revenue_before", sa.Float(), server_default="0", nullable=False),
            sa.Column("revenue_after", sa.Float(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── tasks ──
    if not _table_exists("tasks"):
        op.create_table(
            "tasks",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("store_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=300), nullable=False),
            sa.Column("description", sa.Text(), server_default="", nullable=False),
            sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
            sa.Column("priority", sa.String(length=50), server_default="medium", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    for tbl in (
        "campaign_results", "marketing_campaigns", "agent_approvals",
        "agent_traces", "agent_memories", "tenant_knowledge_documents",
        "knowledge_documents", "tasks",
        "external_factors", "sku_performance", "business_metrics_daily",
        "staff", "stores", "users",
    ):
        if _table_exists(tbl):
            op.drop_table(tbl)
