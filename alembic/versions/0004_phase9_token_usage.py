"""phase 9 token usage tracking

Revision ID: 0004_phase9_token_usage
Revises: 0003_phase5_background_ops
Create Date: 2026-03-15 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_phase9_token_usage"
down_revision = "0003_phase5_background_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "token_usage_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usage_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("panel_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("factor_id", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usage_id"),
    )
    op.create_index("ix_token_usage_log_usage_id", "token_usage_log", ["usage_id"], unique=True)
    op.create_index("ix_token_usage_log_run_id", "token_usage_log", ["run_id"], unique=False)
    op.create_index("ix_token_usage_log_panel_id", "token_usage_log", ["panel_id"], unique=False)
    op.create_index("ix_token_usage_log_agent_id", "token_usage_log", ["agent_id"], unique=False)
    op.create_index("ix_token_usage_log_factor_id", "token_usage_log", ["factor_id"], unique=False)
    op.create_index(
        "ix_token_usage_log_provider", "token_usage_log", ["provider"], unique=False
    )
    op.create_index(
        "ix_token_usage_log_created_at", "token_usage_log", ["created_at"], unique=False
    )

    op.alter_column("token_usage_log", "estimated_cost_usd", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_token_usage_log_created_at", table_name="token_usage_log")
    op.drop_index("ix_token_usage_log_provider", table_name="token_usage_log")
    op.drop_index("ix_token_usage_log_factor_id", table_name="token_usage_log")
    op.drop_index("ix_token_usage_log_agent_id", table_name="token_usage_log")
    op.drop_index("ix_token_usage_log_panel_id", table_name="token_usage_log")
    op.drop_index("ix_token_usage_log_run_id", table_name="token_usage_log")
    op.drop_index("ix_token_usage_log_usage_id", table_name="token_usage_log")
    op.drop_table("token_usage_log")
