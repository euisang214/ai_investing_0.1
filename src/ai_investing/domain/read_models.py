from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from ai_investing.domain.enums import (
    AlertLevel,
    CoverageStatus,
    MonitoringChangeType,
    NotificationCategory,
    NotificationStatus,
    RefreshJobStatus,
    RefreshJobTrigger,
    ReviewNextAction,
    ReviewStatus,
    RunKind,
    RunStatus,
)
from ai_investing.domain.models import (
    ClaimCard,
    DomainModel,
    GatekeeperVerdict,
    MonitoringDelta,
    MonitoringReference,
    NotificationEvent,
    PanelVerdict,
    RefreshJobRecord,
    ReviewQueueEntry,
    SkippedPanelResult,
)


class MonitoringSectionChange(DomainModel):
    section_id: str
    label: str


class CompanyMonitoringHistoryEntry(DomainModel):
    run_id: str
    run_kind: RunKind | None = None
    run_status: RunStatus | None = None
    recorded_at: datetime
    changed_sections: list[MonitoringSectionChange] = Field(default_factory=list)
    delta: MonitoringDelta


class CompanyMonitoringHistory(DomainModel):
    company_id: str
    company_name: str
    coverage_status: CoverageStatus
    entries: list[CompanyMonitoringHistoryEntry] = Field(default_factory=list)


class PortfolioMonitoringCompanyItem(DomainModel):
    company_id: str
    company_name: str
    coverage_status: CoverageStatus
    current_run_id: str
    alert_level: AlertLevel
    recorded_at: datetime
    change_summary: str
    changed_sections: list[MonitoringSectionChange] = Field(default_factory=list)
    trigger_categories: list[MonitoringChangeType] = Field(default_factory=list)
    factor_ids: list[str] = Field(default_factory=list)


class PortfolioMonitoringSegment(DomainModel):
    coverage_status: CoverageStatus
    company_count: int = 0
    companies: list[PortfolioMonitoringCompanyItem] = Field(default_factory=list)


class PortfolioSharedRiskCluster(DomainModel):
    factor_id: str
    label: str
    summary: str
    categories: list[MonitoringChangeType] = Field(default_factory=list)
    portfolio: PortfolioMonitoringSegment
    watchlist: PortfolioMonitoringSegment


class PortfolioAnalogDrilldown(DomainModel):
    company_id: str
    company_name: str
    coverage_status: CoverageStatus
    references: list[MonitoringReference] = Field(default_factory=list)


class PortfolioMonitoringChangeGroup(DomainModel):
    change_type: MonitoringChangeType
    label: str
    summary: str
    portfolio: PortfolioMonitoringSegment
    watchlist: PortfolioMonitoringSegment


class PortfolioMonitoringSummary(DomainModel):
    generated_at: datetime
    included_segments: list[CoverageStatus] = Field(default_factory=list)
    portfolio_company_count: int = 0
    watchlist_company_count: int = 0
    shared_risk_clusters: list[PortfolioSharedRiskCluster] = Field(default_factory=list)
    change_groups: list[PortfolioMonitoringChangeGroup] = Field(default_factory=list)
    exploratory_analog_drilldown: list[PortfolioAnalogDrilldown] = Field(default_factory=list)


class QueueStatusCount(DomainModel):
    status: RefreshJobStatus
    count: int = 0


class QueueJobListItem(DomainModel):
    job_id: str
    company_id: str
    company_name: str
    coverage_status: CoverageStatus
    run_kind: RunKind
    trigger: RefreshJobTrigger
    status: RefreshJobStatus
    requested_at: datetime
    available_at: datetime
    run_id: str | None = None
    review_entry_id: str | None = None
    worker_id: str | None = None
    attempt_count: int = 0


class QueueSummary(DomainModel):
    total_jobs: int = 0
    active_company_count: int = 0
    queued_count: int = 0
    by_status: list[QueueStatusCount] = Field(default_factory=list)
    jobs: list[QueueJobListItem] = Field(default_factory=list)


class QueueJobDetail(DomainModel):
    job: RefreshJobRecord
    review: ReviewQueueEntry | None = None
    notifications: list[NotificationEvent] = Field(default_factory=list)
    run_status: RunStatus | None = None


class ReviewQueueListItem(DomainModel):
    review_id: str
    company_id: str
    company_name: str
    coverage_status: CoverageStatus
    run_id: str
    job_id: str | None = None
    status: ReviewStatus
    next_action: ReviewNextAction
    created_at: datetime
    notification_event_id: str | None = None
    reason_summary: str


class NotificationEventListItem(DomainModel):
    event_id: str
    category: NotificationCategory
    status: NotificationStatus
    company_id: str | None = None
    company_name: str | None = None
    run_id: str | None = None
    job_id: str | None = None
    review_id: str | None = None
    title: str
    next_action: str | None = None
    delivery_attempts: int = 0
    created_at: datetime


class PanelRunRead(DomainModel):
    claims: list[ClaimCard] = Field(default_factory=list)
    verdict: GatekeeperVerdict | PanelVerdict | None = None
    skip: SkippedPanelResult | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> PanelRunRead:
        if self.verdict is None and self.skip is None:
            raise ValueError("PanelRunRead requires either verdict or skip")
        if self.verdict is not None and self.skip is not None:
            raise ValueError("PanelRunRead cannot contain both verdict and skip")
        return self
