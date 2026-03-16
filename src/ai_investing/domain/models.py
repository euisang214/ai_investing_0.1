from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from ai_investing.domain.enums import (
    AlertLevel,
    Cadence,
    ChangeClassification,
    CompanyType,
    CoverageStatus,
    GateDecision,
    MemoSectionStatus,
    NotificationCategory,
    NotificationStatus,
    RecordStatus,
    RefreshJobStatus,
    RefreshJobTrigger,
    ReviewNextAction,
    ReviewStatus,
    RunContinueAction,
    RunKind,
    RunStatus,
    VerdictRecommendation,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class TokenUsage(DomainModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class SourceRef(DomainModel):
    label: str
    url: str | None = None
    page: str | None = None
    excerpt: str | None = None


class EvidenceSnippet(DomainModel):
    summary: str
    source_ref: SourceRef


class SectionImpact(DomainModel):
    section_id: str
    rationale: str


class FactorSignal(DomainModel):
    stance: str
    summary: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class CoverageEntry(DomainModel):
    company_id: str
    company_name: str
    company_type: CompanyType
    coverage_status: CoverageStatus
    cadence: Cadence = Cadence.WEEKLY
    enabled: bool = True
    schedule_policy_id: str | None = None
    schedule_enabled: bool | None = None
    preferred_run_time: str | None = None
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    panel_policy: str = "weekly_default"
    memo_label_profile: str = "default"
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_schedule_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        raw_preferred_run_time = payload.get("preferred_run_time")
        if raw_preferred_run_time in ("", None):
            payload["preferred_run_time"] = None
        elif isinstance(raw_preferred_run_time, str):
            normalized_time = raw_preferred_run_time.strip()
            pieces = normalized_time.split(":")
            if len(pieces) not in {2, 3}:
                raise ValueError("preferred_run_time must use HH:MM or HH:MM:SS format")
            try:
                hour = int(pieces[0])
                minute = int(pieces[1])
                second = int(pieces[2]) if len(pieces) == 3 else 0
            except ValueError as exc:
                raise ValueError("preferred_run_time must be a valid time") from exc
            if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                raise ValueError("preferred_run_time must be a valid time")
            payload["preferred_run_time"] = f"{hour:02d}:{minute:02d}"
        else:
            raise ValueError("preferred_run_time must be a string")

        cadence = payload.get("cadence", Cadence.WEEKLY)
        if isinstance(cadence, Cadence):
            cadence_value = cadence.value
        else:
            cadence_value = str(cadence)

        schedule_policy_id = payload.get("schedule_policy_id")
        schedule_enabled = payload.get("schedule_enabled")
        if schedule_enabled is None:
            schedule_enabled = cadence_value != Cadence.MANUAL.value

        if schedule_policy_id is None and cadence_value == Cadence.WEEKLY.value:
            schedule_policy_id = "weekly"

        payload["schedule_enabled"] = bool(schedule_enabled)
        payload["schedule_policy_id"] = schedule_policy_id
        payload["cadence"] = (
            Cadence.WEEKLY.value if payload["schedule_enabled"] else Cadence.MANUAL.value
        )
        return payload


class CompanyProfile(DomainModel):
    company_id: str
    company_name: str
    company_type: CompanyType
    description: str
    sector: str | None = None
    headquarters: str | None = None
    tags: list[str] = Field(default_factory=list)
    namespace: str
    created_at: datetime = Field(default_factory=lambda: utc_now())
    updated_at: datetime = Field(default_factory=lambda: utc_now())


class EvidenceRecord(DomainModel):
    evidence_id: str = Field(default_factory=lambda: new_id("evd"))
    company_id: str
    company_type: CompanyType
    source_type: str
    title: str
    body: str
    source_path: str
    namespace: str
    panel_ids: list[str] = Field(default_factory=list)
    factor_ids: list[str] = Field(default_factory=list)
    factor_signals: dict[str, FactorSignal] = Field(default_factory=dict)
    source_refs: list[SourceRef] = Field(default_factory=list)
    evidence_quality: float = 0.5
    staleness_days: int = 0
    as_of_date: datetime
    period: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: utc_now())


class ClaimCard(DomainModel):
    claim_id: str = Field(default_factory=lambda: new_id("clm"))
    company_id: str
    company_type: CompanyType
    run_id: str
    panel_id: str
    factor_id: str
    agent_id: str
    claim: str
    bull_case: str
    bear_case: str
    evidence_for: list[EvidenceSnippet] = Field(default_factory=list)
    evidence_against: list[EvidenceSnippet] = Field(default_factory=list)
    confidence: float
    evidence_quality: float
    staleness_assessment: str
    time_horizon: str
    durability_horizon: str
    falsifiers: list[str] = Field(default_factory=list)
    what_changed: str
    unresolved_questions: list[str] = Field(default_factory=list)
    recommended_followups: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    section_impacts: list[SectionImpact] = Field(default_factory=list)
    namespace: str
    status: RecordStatus = RecordStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: utc_now())
    supersedes_claim_id: str | None = None

    @model_validator(mode="after")
    def validate_confidence(self) -> ClaimCard:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not 0 <= self.evidence_quality <= 1:
            raise ValueError("evidence_quality must be between 0 and 1")
        return self


class PanelVerdict(DomainModel):
    verdict_id: str = Field(default_factory=lambda: new_id("vrd"))
    company_id: str
    company_type: CompanyType
    run_id: str
    panel_id: str
    panel_name: str
    summary: str
    recommendation: VerdictRecommendation
    score: float
    confidence: float
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    affected_section_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    namespace: str
    status: RecordStatus = RecordStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: utc_now())
    supersedes_verdict_id: str | None = None


class GatekeeperVerdict(PanelVerdict):
    gate_decision: GateDecision
    gate_reasons: list[str] = Field(default_factory=list)


class PanelSupportAssessment(DomainModel):
    panel_id: str
    panel_name: str
    company_type: CompanyType
    status: Literal["supported", "weak_confidence", "unsupported"]
    reason: str
    evidence_count: int = 0
    factor_coverage_ratio: float = 0.0
    evidence_summary: str
    available_evidence_families: list[str] = Field(default_factory=list)
    missing_evidence_families: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
    weak_confidence_allowed: bool = False


class SkippedPanelResult(DomainModel):
    panel_id: str
    panel_name: str
    company_type: CompanyType
    status: Literal["skipped"] = "skipped"
    reason_code: str
    reason: str
    evidence_summary: str
    evidence_count: int = 0
    factor_coverage_ratio: float = 0.0
    available_evidence_families: list[str] = Field(default_factory=list)
    missing_evidence_families: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)


class MemoSection(DomainModel):
    section_id: str
    label: str
    content: str
    status: MemoSectionStatus = MemoSectionStatus.PENDING
    supporting_claim_ids: list[str] = Field(default_factory=list)
    supporting_verdict_ids: list[str] = Field(default_factory=list)
    updated_by_run_id: str | None = None
    updated_at: datetime = Field(default_factory=lambda: utc_now())


class MemoSectionUpdate(DomainModel):
    update_id: str = Field(default_factory=lambda: new_id("msu"))
    company_id: str
    section_id: str
    prior_summary: str
    updated_text: str
    change_classification: ChangeClassification
    supporting_claim_ids: list[str] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)
    updated_by_run_id: str
    updated_at: datetime = Field(default_factory=lambda: utc_now())


class ICMemo(DomainModel):
    memo_id: str = Field(default_factory=lambda: new_id("memo"))
    company_id: str
    run_id: str
    is_active: bool = True
    is_initial_coverage: bool = False
    sections: list[MemoSection]
    recommendation_summary: str
    namespace: str
    created_at: datetime = Field(default_factory=lambda: utc_now())
    updated_at: datetime = Field(default_factory=lambda: utc_now())

    def section_map(self) -> dict[str, MemoSection]:
        return {section.section_id: section for section in self.sections}


class MonitoringReason(DomainModel):
    category: str
    summary: str
    factor_id: str | None = None
    severity: str = "info"
    related_section_ids: list[str] = Field(default_factory=list)


class MonitoringReference(DomainModel):
    category: str
    label: str
    rationale: str
    factor_id: str | None = None
    company_id: str | None = None
    company_name: str | None = None
    source_ref: SourceRef | None = None
    score: float | None = None


class MonitoringCurrentState(DomainModel):
    category: str
    label: str
    factor_id: str
    state: str
    summary: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class MonitoringDelta(DomainModel):
    delta_id: str = Field(default_factory=lambda: new_id("dlt"))
    company_id: str
    prior_run_id: str | None = None
    current_run_id: str
    changed_claim_ids: list[str] = Field(default_factory=list)
    changed_sections: list[str] = Field(default_factory=list)
    change_summary: str
    thesis_drift_flags: list[str] = Field(default_factory=list)
    alert_level: AlertLevel
    trigger_reasons: list[MonitoringReason] = Field(default_factory=list)
    contradiction_references: list[MonitoringReference] = Field(default_factory=list)
    analog_references: list[MonitoringReference] = Field(default_factory=list)
    concentration_signals: list[MonitoringCurrentState] = Field(default_factory=list)
    panel_change_hints: list[MonitoringReason] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: utc_now())

    @model_serializer(mode="wrap")
    def serialize(self, serializer):
        data = serializer(self)
        for field_name in (
            "trigger_reasons",
            "contradiction_references",
            "analog_references",
            "concentration_signals",
            "panel_change_hints",
        ):
            if not data.get(field_name):
                data.pop(field_name, None)
        return data


class ToolInvocationLog(DomainModel):
    log_id: str = Field(default_factory=lambda: new_id("tool"))
    run_id: str
    agent_id: str
    tool_id: str
    input_summary: str
    output_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: utc_now())


class RunCheckpoint(DomainModel):
    checkpoint_panel_id: str
    allowed_actions: list[RunContinueAction] = Field(default_factory=list)
    provisional_required: bool = False
    note: str | None = None
    requested_at: datetime = Field(default_factory=lambda: utc_now())
    resolved_at: datetime | None = None
    resolution_action: RunContinueAction | None = None


class RunRecord(DomainModel):
    run_id: str = Field(default_factory=lambda: new_id("run"))
    company_id: str
    run_kind: RunKind
    status: RunStatus = RunStatus.PENDING
    triggered_by: str = "system"
    panel_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: utc_now())
    completed_at: datetime | None = None
    gate_decision: GateDecision | None = None
    awaiting_continue: bool = False
    gated_out: bool = False
    provisional: bool = False
    stopped_after_panel: str | None = None
    checkpoint_panel_id: str | None = None
    checkpoint: RunCheckpoint | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RefreshJobRecord(DomainModel):
    job_id: str = Field(default_factory=lambda: new_id("job"))
    company_id: str
    company_name: str
    coverage_status: CoverageStatus
    run_kind: RunKind = RunKind.REFRESH
    trigger: RefreshJobTrigger = RefreshJobTrigger.SCHEDULED
    status: RefreshJobStatus = RefreshJobStatus.QUEUED
    requested_by: str = "system"
    priority: int = 100
    scheduled_for: datetime | None = None
    available_at: datetime = Field(default_factory=lambda: utc_now())
    requested_at: datetime = Field(default_factory=lambda: utc_now())
    claimed_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    run_id: str | None = None
    review_entry_id: str | None = None
    worker_id: str | None = None
    claim_token: str | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    cancellation_reason: str | None = None
    failure_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_job_counts(self) -> RefreshJobRecord:
        if self.priority < 0:
            raise ValueError("priority must be non-negative")
        if self.attempt_count < 0:
            raise ValueError("attempt_count must be non-negative")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        return self


class ReviewQueueEntry(DomainModel):
    review_id: str = Field(default_factory=lambda: new_id("rev"))
    company_id: str
    company_name: str
    coverage_status: CoverageStatus
    run_id: str
    job_id: str | None = None
    gate_decision: GateDecision = GateDecision.FAIL
    checkpoint_panel_id: str = "gatekeepers"
    status: ReviewStatus = ReviewStatus.OPEN
    next_action: ReviewNextAction = ReviewNextAction.CONTINUE_PROVISIONAL
    reason_summary: str
    notification_event_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: utc_now())
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    resolution_note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationEvent(DomainModel):
    event_id: str = Field(default_factory=lambda: new_id("ntf"))
    category: NotificationCategory
    status: NotificationStatus = NotificationStatus.PENDING
    company_id: str | None = None
    company_name: str | None = None
    coverage_status: CoverageStatus | None = None
    run_id: str | None = None
    job_id: str | None = None
    review_id: str | None = None
    channel: str = "operator"
    title: str
    summary: str
    next_action: str | None = None
    claimed_by: str | None = None
    claim_token: str | None = None
    claimed_at: datetime | None = None
    dispatched_at: datetime | None = None
    acknowledged_at: datetime | None = None
    delivery_attempts: int = 0
    last_error: str | None = None
    digest_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: utc_now())

    @model_validator(mode="after")
    def validate_delivery_attempts(self) -> NotificationEvent:
        if self.delivery_attempts < 0:
            raise ValueError("delivery_attempts must be non-negative")
        return self

class TokenUsageRecord(DomainModel):
    """Tracks token usage for a single LLM call."""

    usage_id: str = Field(default_factory=lambda: new_id("tok"))
    run_id: str
    panel_id: str
    agent_id: str
    factor_id: str | None = None
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=lambda: utc_now())


class StructuredGenerationRequest(DomainModel):
    task_type: str
    prompt: str
    input_data: dict[str, Any]


class WriteMemoSectionInput(DomainModel):
    company_id: str
    section_id: str
    label: str
    content: str
    run_id: str
    supporting_claim_ids: list[str] = Field(default_factory=list)
    supporting_verdict_ids: list[str] = Field(default_factory=list)
