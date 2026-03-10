"""phase 1 baseline schema

Revision ID: 0001_phase1_baseline
Revises:
Create Date: 2026-03-10 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_phase1_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coverage_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("company_type", sa.String(length=32), nullable=False),
        sa.Column("coverage_status", sa.String(length=32), nullable=False),
        sa.Column("cadence", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("panel_policy", sa.String(length=64), nullable=False),
        sa.Column("memo_label_profile", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
    )
    op.create_index("ix_coverage_entries_company_id", "coverage_entries", ["company_id"], unique=True)
    op.create_index("ix_coverage_entries_company_type", "coverage_entries", ["company_type"], unique=False)
    op.create_index(
        "ix_coverage_entries_coverage_status",
        "coverage_entries",
        ["coverage_status"],
        unique=False,
    )

    op.create_table(
        "company_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
    )
    op.create_index("ix_company_profiles_company_id", "company_profiles", ["company_id"], unique=True)

    op.create_table(
        "run_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("run_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("panel_id", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_run_records_run_id", "run_records", ["run_id"], unique=True)
    op.create_index("ix_run_records_company_id", "run_records", ["company_id"], unique=False)
    op.create_index("ix_run_records_run_kind", "run_records", ["run_kind"], unique=False)
    op.create_index("ix_run_records_status", "run_records", ["status"], unique=False)
    op.create_index("ix_run_records_started_at", "run_records", ["started_at"], unique=False)

    op.create_table(
        "evidence_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("company_type", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("as_of_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id"),
    )
    op.create_index("ix_evidence_records_evidence_id", "evidence_records", ["evidence_id"], unique=True)
    op.create_index("ix_evidence_records_company_id", "evidence_records", ["company_id"], unique=False)
    op.create_index("ix_evidence_records_company_type", "evidence_records", ["company_type"], unique=False)
    op.create_index("ix_evidence_records_source_type", "evidence_records", ["source_type"], unique=False)
    op.create_index("ix_evidence_records_namespace", "evidence_records", ["namespace"], unique=False)
    op.create_index("ix_evidence_records_as_of_date", "evidence_records", ["as_of_date"], unique=False)

    op.create_table(
        "claim_cards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("panel_id", sa.String(length=64), nullable=False),
        sa.Column("factor_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id"),
    )
    op.create_index("ix_claim_cards_claim_id", "claim_cards", ["claim_id"], unique=True)
    op.create_index("ix_claim_cards_company_id", "claim_cards", ["company_id"], unique=False)
    op.create_index("ix_claim_cards_run_id", "claim_cards", ["run_id"], unique=False)
    op.create_index("ix_claim_cards_panel_id", "claim_cards", ["panel_id"], unique=False)
    op.create_index("ix_claim_cards_factor_id", "claim_cards", ["factor_id"], unique=False)
    op.create_index("ix_claim_cards_agent_id", "claim_cards", ["agent_id"], unique=False)
    op.create_index("ix_claim_cards_status", "claim_cards", ["status"], unique=False)
    op.create_index("ix_claim_cards_namespace", "claim_cards", ["namespace"], unique=False)
    op.create_index("ix_claim_cards_created_at", "claim_cards", ["created_at"], unique=False)

    op.create_table(
        "panel_verdicts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("verdict_id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("panel_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("verdict_id"),
    )
    op.create_index("ix_panel_verdicts_verdict_id", "panel_verdicts", ["verdict_id"], unique=True)
    op.create_index("ix_panel_verdicts_company_id", "panel_verdicts", ["company_id"], unique=False)
    op.create_index("ix_panel_verdicts_run_id", "panel_verdicts", ["run_id"], unique=False)
    op.create_index("ix_panel_verdicts_panel_id", "panel_verdicts", ["panel_id"], unique=False)
    op.create_index("ix_panel_verdicts_status", "panel_verdicts", ["status"], unique=False)
    op.create_index("ix_panel_verdicts_namespace", "panel_verdicts", ["namespace"], unique=False)
    op.create_index("ix_panel_verdicts_created_at", "panel_verdicts", ["created_at"], unique=False)

    op.create_table(
        "memos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("memo_id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("memo_id"),
    )
    op.create_index("ix_memos_memo_id", "memos", ["memo_id"], unique=True)
    op.create_index("ix_memos_company_id", "memos", ["company_id"], unique=False)
    op.create_index("ix_memos_run_id", "memos", ["run_id"], unique=False)
    op.create_index("ix_memos_is_active", "memos", ["is_active"], unique=False)
    op.create_index("ix_memos_created_at", "memos", ["created_at"], unique=False)
    op.create_index("ix_memos_updated_at", "memos", ["updated_at"], unique=False)

    op.create_table(
        "memo_section_updates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("update_id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("section_id", sa.String(length=64), nullable=False),
        sa.Column("updated_by_run_id", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("update_id"),
    )
    op.create_index(
        "ix_memo_section_updates_update_id",
        "memo_section_updates",
        ["update_id"],
        unique=True,
    )
    op.create_index(
        "ix_memo_section_updates_company_id",
        "memo_section_updates",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_memo_section_updates_section_id",
        "memo_section_updates",
        ["section_id"],
        unique=False,
    )
    op.create_index(
        "ix_memo_section_updates_updated_by_run_id",
        "memo_section_updates",
        ["updated_by_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_memo_section_updates_updated_at",
        "memo_section_updates",
        ["updated_at"],
        unique=False,
    )

    op.create_table(
        "monitoring_deltas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("delta_id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("current_run_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("delta_id"),
    )
    op.create_index("ix_monitoring_deltas_delta_id", "monitoring_deltas", ["delta_id"], unique=True)
    op.create_index(
        "ix_monitoring_deltas_company_id",
        "monitoring_deltas",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_monitoring_deltas_current_run_id",
        "monitoring_deltas",
        ["current_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_monitoring_deltas_created_at",
        "monitoring_deltas",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "tool_invocation_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("log_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("tool_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("log_id"),
    )
    op.create_index(
        "ix_tool_invocation_logs_log_id",
        "tool_invocation_logs",
        ["log_id"],
        unique=True,
    )
    op.create_index(
        "ix_tool_invocation_logs_run_id",
        "tool_invocation_logs",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_invocation_logs_agent_id",
        "tool_invocation_logs",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_invocation_logs_tool_id",
        "tool_invocation_logs",
        ["tool_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_invocation_logs_created_at",
        "tool_invocation_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tool_invocation_logs_created_at", table_name="tool_invocation_logs")
    op.drop_index("ix_tool_invocation_logs_tool_id", table_name="tool_invocation_logs")
    op.drop_index("ix_tool_invocation_logs_agent_id", table_name="tool_invocation_logs")
    op.drop_index("ix_tool_invocation_logs_run_id", table_name="tool_invocation_logs")
    op.drop_index("ix_tool_invocation_logs_log_id", table_name="tool_invocation_logs")
    op.drop_table("tool_invocation_logs")

    op.drop_index("ix_monitoring_deltas_created_at", table_name="monitoring_deltas")
    op.drop_index("ix_monitoring_deltas_current_run_id", table_name="monitoring_deltas")
    op.drop_index("ix_monitoring_deltas_company_id", table_name="monitoring_deltas")
    op.drop_index("ix_monitoring_deltas_delta_id", table_name="monitoring_deltas")
    op.drop_table("monitoring_deltas")

    op.drop_index("ix_memo_section_updates_updated_at", table_name="memo_section_updates")
    op.drop_index(
        "ix_memo_section_updates_updated_by_run_id",
        table_name="memo_section_updates",
    )
    op.drop_index("ix_memo_section_updates_section_id", table_name="memo_section_updates")
    op.drop_index("ix_memo_section_updates_company_id", table_name="memo_section_updates")
    op.drop_index("ix_memo_section_updates_update_id", table_name="memo_section_updates")
    op.drop_table("memo_section_updates")

    op.drop_index("ix_memos_updated_at", table_name="memos")
    op.drop_index("ix_memos_created_at", table_name="memos")
    op.drop_index("ix_memos_is_active", table_name="memos")
    op.drop_index("ix_memos_run_id", table_name="memos")
    op.drop_index("ix_memos_company_id", table_name="memos")
    op.drop_index("ix_memos_memo_id", table_name="memos")
    op.drop_table("memos")

    op.drop_index("ix_panel_verdicts_created_at", table_name="panel_verdicts")
    op.drop_index("ix_panel_verdicts_namespace", table_name="panel_verdicts")
    op.drop_index("ix_panel_verdicts_status", table_name="panel_verdicts")
    op.drop_index("ix_panel_verdicts_panel_id", table_name="panel_verdicts")
    op.drop_index("ix_panel_verdicts_run_id", table_name="panel_verdicts")
    op.drop_index("ix_panel_verdicts_company_id", table_name="panel_verdicts")
    op.drop_index("ix_panel_verdicts_verdict_id", table_name="panel_verdicts")
    op.drop_table("panel_verdicts")

    op.drop_index("ix_claim_cards_created_at", table_name="claim_cards")
    op.drop_index("ix_claim_cards_namespace", table_name="claim_cards")
    op.drop_index("ix_claim_cards_status", table_name="claim_cards")
    op.drop_index("ix_claim_cards_agent_id", table_name="claim_cards")
    op.drop_index("ix_claim_cards_factor_id", table_name="claim_cards")
    op.drop_index("ix_claim_cards_panel_id", table_name="claim_cards")
    op.drop_index("ix_claim_cards_run_id", table_name="claim_cards")
    op.drop_index("ix_claim_cards_company_id", table_name="claim_cards")
    op.drop_index("ix_claim_cards_claim_id", table_name="claim_cards")
    op.drop_table("claim_cards")

    op.drop_index("ix_evidence_records_as_of_date", table_name="evidence_records")
    op.drop_index("ix_evidence_records_namespace", table_name="evidence_records")
    op.drop_index("ix_evidence_records_source_type", table_name="evidence_records")
    op.drop_index("ix_evidence_records_company_type", table_name="evidence_records")
    op.drop_index("ix_evidence_records_company_id", table_name="evidence_records")
    op.drop_index("ix_evidence_records_evidence_id", table_name="evidence_records")
    op.drop_table("evidence_records")

    op.drop_index("ix_run_records_started_at", table_name="run_records")
    op.drop_index("ix_run_records_status", table_name="run_records")
    op.drop_index("ix_run_records_run_kind", table_name="run_records")
    op.drop_index("ix_run_records_company_id", table_name="run_records")
    op.drop_index("ix_run_records_run_id", table_name="run_records")
    op.drop_table("run_records")

    op.drop_index("ix_company_profiles_company_id", table_name="company_profiles")
    op.drop_table("company_profiles")

    op.drop_index("ix_coverage_entries_coverage_status", table_name="coverage_entries")
    op.drop_index("ix_coverage_entries_company_type", table_name="coverage_entries")
    op.drop_index("ix_coverage_entries_company_id", table_name="coverage_entries")
    op.drop_table("coverage_entries")
