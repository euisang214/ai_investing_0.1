from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ai_investing.domain.enums import (
    AlertLevel,
    CoverageStatus,
    MonitoringChangeType,
    RunKind,
    RunStatus,
)
from ai_investing.domain.models import DomainModel, MonitoringDelta, MonitoringReference


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
