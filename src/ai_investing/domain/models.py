from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_investing.domain.enums import (
    AlertLevel,
    Cadence,
    ChangeClassification,
    CompanyType,
    CoverageStatus,
    GateDecision,
    MemoSectionStatus,
    RecordStatus,
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
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    panel_policy: str = "weekly_default"
    memo_label_profile: str = "default"
    notes: str | None = None


class CompanyProfile(DomainModel):
    company_id: str
    company_name: str
    company_type: CompanyType
    description: str
    sector: str | None = None
    headquarters: str | None = None
    tags: list[str] = Field(default_factory=list)
    namespace: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


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
    created_at: datetime = Field(default_factory=utc_now)


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
    created_at: datetime = Field(default_factory=utc_now)
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
    created_at: datetime = Field(default_factory=utc_now)
    supersedes_verdict_id: str | None = None


class GatekeeperVerdict(PanelVerdict):
    gate_decision: GateDecision
    gate_reasons: list[str] = Field(default_factory=list)


class MemoSection(DomainModel):
    section_id: str
    label: str
    content: str
    status: MemoSectionStatus = MemoSectionStatus.PENDING
    supporting_claim_ids: list[str] = Field(default_factory=list)
    supporting_verdict_ids: list[str] = Field(default_factory=list)
    updated_by_run_id: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


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
    updated_at: datetime = Field(default_factory=utc_now)


class ICMemo(DomainModel):
    memo_id: str = Field(default_factory=lambda: new_id("memo"))
    company_id: str
    run_id: str
    is_active: bool = True
    is_initial_coverage: bool = False
    sections: list[MemoSection]
    recommendation_summary: str
    namespace: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def section_map(self) -> dict[str, MemoSection]:
        return {section.section_id: section for section in self.sections}


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
    created_at: datetime = Field(default_factory=utc_now)


class ToolInvocationLog(DomainModel):
    log_id: str = Field(default_factory=lambda: new_id("tool"))
    run_id: str
    agent_id: str
    tool_id: str
    input_summary: str
    output_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class RunRecord(DomainModel):
    run_id: str = Field(default_factory=lambda: new_id("run"))
    company_id: str
    run_kind: RunKind
    status: RunStatus = RunStatus.PENDING
    triggered_by: str = "system"
    panel_id: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


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
