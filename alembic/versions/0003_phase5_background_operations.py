"""phase 5 background operations schema

Revision ID: 0003_phase5_background_operations
Revises: 0002_phase2_checkpoint_runtime
Create Date: 2026-03-13 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_phase5_background_operations"
down_revision = "0002_phase2_checkpoint_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("coverage_status", sa.String(length=32), nullable=False),
        sa.Column("run_kind", sa.String(length=32), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_by", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("review_entry_id", sa.String(length=64), nullable=True),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("claim_token", sa.String(length=64), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_refresh_jobs_company_id", "refresh_jobs", ["company_id"], unique=False)
    op.create_index(
        "ix_refresh_jobs_coverage_status",
        "refresh_jobs",
        ["coverage_status"],
        unique=False,
    )
    op.create_index("ix_refresh_jobs_run_kind", "refresh_jobs", ["run_kind"], unique=False)
    op.create_index("ix_refresh_jobs_trigger", "refresh_jobs", ["trigger"], unique=False)
    op.create_index("ix_refresh_jobs_status", "refresh_jobs", ["status"], unique=False)
    op.create_index(
        "ix_refresh_jobs_requested_by",
        "refresh_jobs",
        ["requested_by"],
        unique=False,
    )
    op.create_index("ix_refresh_jobs_priority", "refresh_jobs", ["priority"], unique=False)
    op.create_index(
        "ix_refresh_jobs_available_at",
        "refresh_jobs",
        ["available_at"],
        unique=False,
    )
    op.create_index(
        "ix_refresh_jobs_requested_at",
        "refresh_jobs",
        ["requested_at"],
        unique=False,
    )
    op.create_index("ix_refresh_jobs_run_id", "refresh_jobs", ["run_id"], unique=False)
    op.create_index(
        "ix_refresh_jobs_review_entry_id",
        "refresh_jobs",
        ["review_entry_id"],
        unique=False,
    )
    op.create_index("ix_refresh_jobs_worker_id", "refresh_jobs", ["worker_id"], unique=False)
    op.create_index(
        "ix_refresh_jobs_claim_token",
        "refresh_jobs",
        ["claim_token"],
        unique=False,
    )

    op.create_table(
        "review_queue_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("review_id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("coverage_status", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("gate_decision", sa.String(length=32), nullable=False),
        sa.Column("checkpoint_panel_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("next_action", sa.String(length=64), nullable=False),
        sa.Column("notification_event_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_id"),
    )
    op.create_index(
        "ix_review_queue_entries_company_id",
        "review_queue_entries",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_queue_entries_coverage_status",
        "review_queue_entries",
        ["coverage_status"],
        unique=False,
    )
    op.create_index(
        "ix_review_queue_entries_run_id",
        "review_queue_entries",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_queue_entries_job_id",
        "review_queue_entries",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_queue_entries_gate_decision",
        "review_queue_entries",
        ["gate_decision"],
        unique=False,
    )
    op.create_index(
        "ix_review_queue_entries_checkpoint_panel_id",
        "review_queue_entries",
        ["checkpoint_panel_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_queue_entries_status",
        "review_queue_entries",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_review_queue_entries_notification_event_id",
        "review_queue_entries",
        ["notification_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_queue_entries_created_at",
        "review_queue_entries",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "notification_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("coverage_status", sa.String(length=32), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("review_id", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("claimed_by", sa.String(length=64), nullable=True),
        sa.Column("claim_token", sa.String(length=64), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("digest_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(
        "ix_notification_events_category",
        "notification_events",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_status",
        "notification_events",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_company_id",
        "notification_events",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_coverage_status",
        "notification_events",
        ["coverage_status"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_run_id",
        "notification_events",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_job_id",
        "notification_events",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_review_id",
        "notification_events",
        ["review_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_channel",
        "notification_events",
        ["channel"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_claimed_by",
        "notification_events",
        ["claimed_by"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_claim_token",
        "notification_events",
        ["claim_token"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_digest_key",
        "notification_events",
        ["digest_key"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_created_at",
        "notification_events",
        ["created_at"],
        unique=False,
    )

    op.alter_column("refresh_jobs", "priority", server_default=None)
    op.alter_column("refresh_jobs", "attempt_count", server_default=None)
    op.alter_column("refresh_jobs", "max_attempts", server_default=None)
    op.alter_column("notification_events", "delivery_attempts", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_notification_events_created_at", table_name="notification_events")
    op.drop_index("ix_notification_events_digest_key", table_name="notification_events")
    op.drop_index("ix_notification_events_claim_token", table_name="notification_events")
    op.drop_index("ix_notification_events_claimed_by", table_name="notification_events")
    op.drop_index("ix_notification_events_channel", table_name="notification_events")
    op.drop_index("ix_notification_events_review_id", table_name="notification_events")
    op.drop_index("ix_notification_events_job_id", table_name="notification_events")
    op.drop_index("ix_notification_events_run_id", table_name="notification_events")
    op.drop_index("ix_notification_events_coverage_status", table_name="notification_events")
    op.drop_index("ix_notification_events_company_id", table_name="notification_events")
    op.drop_index("ix_notification_events_status", table_name="notification_events")
    op.drop_index("ix_notification_events_category", table_name="notification_events")
    op.drop_table("notification_events")

    op.drop_index("ix_review_queue_entries_created_at", table_name="review_queue_entries")
    op.drop_index(
        "ix_review_queue_entries_notification_event_id",
        table_name="review_queue_entries",
    )
    op.drop_index("ix_review_queue_entries_status", table_name="review_queue_entries")
    op.drop_index(
        "ix_review_queue_entries_checkpoint_panel_id",
        table_name="review_queue_entries",
    )
    op.drop_index("ix_review_queue_entries_gate_decision", table_name="review_queue_entries")
    op.drop_index("ix_review_queue_entries_job_id", table_name="review_queue_entries")
    op.drop_index("ix_review_queue_entries_run_id", table_name="review_queue_entries")
    op.drop_index(
        "ix_review_queue_entries_coverage_status",
        table_name="review_queue_entries",
    )
    op.drop_index("ix_review_queue_entries_company_id", table_name="review_queue_entries")
    op.drop_table("review_queue_entries")

    op.drop_index("ix_refresh_jobs_claim_token", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_worker_id", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_review_entry_id", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_run_id", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_requested_at", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_available_at", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_priority", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_requested_by", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_status", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_trigger", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_run_kind", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_coverage_status", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_company_id", table_name="refresh_jobs")
    op.drop_table("refresh_jobs")
