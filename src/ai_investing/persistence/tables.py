from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CoverageEntryRow(Base):
    __tablename__ = "coverage_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    company_type: Mapped[str] = mapped_column(String(32), index=True)
    coverage_status: Mapped[str] = mapped_column(String(32), index=True)
    cadence: Mapped[str] = mapped_column(String(32))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    panel_policy: Mapped[str] = mapped_column(String(64))
    memo_label_profile: Mapped[str] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class CompanyProfileRow(Base):
    __tablename__ = "company_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class RunRecordRow(Base):
    __tablename__ = "run_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_id: Mapped[str] = mapped_column(String(64), index=True)
    run_kind: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    panel_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gate_decision: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    awaiting_continue: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    gated_out: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    provisional: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    stopped_after_panel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checkpoint_panel_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class EvidenceRecordRow(Base):
    __tablename__ = "evidence_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evidence_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_id: Mapped[str] = mapped_column(String(64), index=True)
    company_type: Mapped[str] = mapped_column(String(32), index=True)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    namespace: Mapped[str] = mapped_column(String(255), index=True)
    as_of_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class ClaimCardRow(Base):
    __tablename__ = "claim_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    panel_id: Mapped[str] = mapped_column(String(64), index=True)
    factor_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    namespace: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class PanelVerdictRow(Base):
    __tablename__ = "panel_verdicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verdict_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    panel_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    namespace: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class MemoRow(Base):
    __tablename__ = "memos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    memo_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class MemoSectionUpdateRow(Base):
    __tablename__ = "memo_section_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    update_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_id: Mapped[str] = mapped_column(String(64), index=True)
    section_id: Mapped[str] = mapped_column(String(64), index=True)
    updated_by_run_id: Mapped[str] = mapped_column(String(64), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class MonitoringDeltaRow(Base):
    __tablename__ = "monitoring_deltas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delta_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_id: Mapped[str] = mapped_column(String(64), index=True)
    current_run_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class ToolInvocationLogRow(Base):
    __tablename__ = "tool_invocation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    tool_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
