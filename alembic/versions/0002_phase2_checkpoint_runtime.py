"""phase 2 checkpoint runtime schema

Revision ID: 0002_phase2_checkpoint_runtime
Revises: 0001_phase1_baseline
Create Date: 2026-03-11 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_phase2_checkpoint_runtime"
down_revision = "0001_phase1_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("run_records", sa.Column("gate_decision", sa.String(length=32), nullable=True))
    op.add_column(
        "run_records",
        sa.Column(
            "awaiting_continue",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "run_records",
        sa.Column("gated_out", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "run_records",
        sa.Column("provisional", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "run_records",
        sa.Column("stopped_after_panel", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "run_records",
        sa.Column("checkpoint_panel_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_run_records_gate_decision", "run_records", ["gate_decision"], unique=False)
    op.create_index(
        "ix_run_records_awaiting_continue",
        "run_records",
        ["awaiting_continue"],
        unique=False,
    )
    op.create_index("ix_run_records_gated_out", "run_records", ["gated_out"], unique=False)
    op.create_index("ix_run_records_provisional", "run_records", ["provisional"], unique=False)
    op.create_index(
        "ix_run_records_checkpoint_panel_id",
        "run_records",
        ["checkpoint_panel_id"],
        unique=False,
    )
    op.alter_column("run_records", "awaiting_continue", server_default=None)
    op.alter_column("run_records", "gated_out", server_default=None)
    op.alter_column("run_records", "provisional", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_run_records_checkpoint_panel_id", table_name="run_records")
    op.drop_index("ix_run_records_provisional", table_name="run_records")
    op.drop_index("ix_run_records_gated_out", table_name="run_records")
    op.drop_index("ix_run_records_awaiting_continue", table_name="run_records")
    op.drop_index("ix_run_records_gate_decision", table_name="run_records")
    op.drop_column("run_records", "checkpoint_panel_id")
    op.drop_column("run_records", "stopped_after_panel")
    op.drop_column("run_records", "provisional")
    op.drop_column("run_records", "gated_out")
    op.drop_column("run_records", "awaiting_continue")
    op.drop_column("run_records", "gate_decision")
