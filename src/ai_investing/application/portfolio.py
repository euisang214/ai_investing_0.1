from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ai_investing.application.context import AppContext
from ai_investing.domain.enums import CoverageStatus, MonitoringChangeType
from ai_investing.domain.models import CoverageEntry, MonitoringDelta, RunRecord, utc_now
from ai_investing.domain.read_models import (
    CompanyMonitoringHistory,
    CompanyMonitoringHistoryEntry,
    MonitoringSectionChange,
    PortfolioAnalogDrilldown,
    PortfolioMonitoringChangeGroup,
    PortfolioMonitoringCompanyItem,
    PortfolioMonitoringSegment,
    PortfolioMonitoringSummary,
    PortfolioSharedRiskCluster,
)
from ai_investing.persistence.repositories import Repository

_SUMMARY_SEGMENTS = (CoverageStatus.PORTFOLIO, CoverageStatus.WATCHLIST)
_CHANGE_ORDER = (
    MonitoringChangeType.CONTRADICTION,
    MonitoringChangeType.THESIS_DRIFT,
    MonitoringChangeType.CONCENTRATION,
    MonitoringChangeType.SECTION_MOVEMENT,
)
_CHANGE_LABELS = {
    MonitoringChangeType.CONTRADICTION: "Contradictions",
    MonitoringChangeType.THESIS_DRIFT: "Thesis Drift",
    MonitoringChangeType.CONCENTRATION: "Concentration Signals",
    MonitoringChangeType.SECTION_MOVEMENT: "Section Movement",
}


def resolve_summary_segments(segment: str) -> tuple[CoverageStatus, ...]:
    normalized = segment.strip().lower()
    if normalized == "all":
        return _SUMMARY_SEGMENTS
    if normalized == CoverageStatus.PORTFOLIO.value:
        return (CoverageStatus.PORTFOLIO,)
    if normalized == CoverageStatus.WATCHLIST.value:
        return (CoverageStatus.WATCHLIST,)
    raise ValueError("segment must be one of: all, portfolio, watchlist.")


@dataclass(frozen=True)
class _MonitoringSnapshot:
    coverage: CoverageEntry
    delta: MonitoringDelta
    changed_sections: tuple[MonitoringSectionChange, ...]
    item: PortfolioMonitoringCompanyItem
    change_types: tuple[MonitoringChangeType, ...]


class PortfolioReadService:
    def __init__(self, context: AppContext):
        self.context = context

    def get_company_monitoring_history(
        self,
        company_id: str,
        *,
        limit: int | None = None,
    ) -> CompanyMonitoringHistory:
        with self.context.database.session() as session:
            repository = Repository(session)
            coverage = repository.get_coverage(company_id)
            if coverage is None:
                raise KeyError(company_id)
            deltas = repository.list_monitoring_deltas(company_id, limit=limit)
            runs = {run.run_id: run for run in repository.list_runs(company_id)}

        entries = [
            self._history_entry(
                delta=delta,
                run=runs.get(delta.current_run_id),
                label_profile=coverage.memo_label_profile,
            )
            for delta in deltas
        ]
        return CompanyMonitoringHistory(
            company_id=coverage.company_id,
            company_name=coverage.company_name,
            coverage_status=coverage.coverage_status,
            entries=entries,
        )

    def get_portfolio_monitoring_summary(
        self,
        *,
        coverage_statuses: tuple[CoverageStatus, ...] | None = None,
    ) -> PortfolioMonitoringSummary:
        selected_statuses = coverage_statuses or _SUMMARY_SEGMENTS
        with self.context.database.session() as session:
            repository = Repository(session)
            coverage_entries = repository.list_coverage(
                enabled_only=True,
                coverage_statuses=selected_statuses,
            )
            delta_map = {
                entry.company_id: repository.get_latest_monitoring_delta(entry.company_id)
                for entry in coverage_entries
            }

        snapshots = [
            self._snapshot(entry, delta)
            for entry, delta in (
                (entry, delta_map.get(entry.company_id)) for entry in coverage_entries
            )
            if delta is not None
        ]
        shared_risk_clusters = self._build_shared_risk_clusters(snapshots)
        change_groups = self._build_change_groups(snapshots)
        analog_drilldown = self._build_analog_drilldown(snapshots)

        portfolio_count = sum(
            1
            for snapshot in snapshots
            if snapshot.coverage.coverage_status == CoverageStatus.PORTFOLIO
        )
        watchlist_count = sum(
            1
            for snapshot in snapshots
            if snapshot.coverage.coverage_status == CoverageStatus.WATCHLIST
        )
        return PortfolioMonitoringSummary(
            generated_at=utc_now(),
            included_segments=list(selected_statuses),
            portfolio_company_count=portfolio_count,
            watchlist_company_count=watchlist_count,
            shared_risk_clusters=shared_risk_clusters,
            change_groups=change_groups,
            exploratory_analog_drilldown=analog_drilldown,
        )

    def _history_entry(
        self,
        *,
        delta: MonitoringDelta,
        run: RunRecord | None,
        label_profile: str,
    ) -> CompanyMonitoringHistoryEntry:
        return CompanyMonitoringHistoryEntry(
            run_id=delta.current_run_id,
            run_kind=run.run_kind if run is not None else None,
            run_status=run.status if run is not None else None,
            recorded_at=delta.created_at,
            changed_sections=self._changed_sections(delta, label_profile=label_profile),
            delta=delta,
        )

    def _snapshot(self, coverage: CoverageEntry, delta: MonitoringDelta) -> _MonitoringSnapshot:
        changed_sections = tuple(
            self._changed_sections(delta, label_profile=coverage.memo_label_profile)
        )
        change_types = tuple(self._change_types(delta))
        item = PortfolioMonitoringCompanyItem(
            company_id=coverage.company_id,
            company_name=coverage.company_name,
            coverage_status=coverage.coverage_status,
            current_run_id=delta.current_run_id,
            alert_level=delta.alert_level,
            recorded_at=delta.created_at,
            change_summary=delta.change_summary,
            changed_sections=list(changed_sections),
            trigger_categories=list(change_types),
            factor_ids=self._factor_ids(delta),
        )
        return _MonitoringSnapshot(
            coverage=coverage,
            delta=delta,
            changed_sections=changed_sections,
            item=item,
            change_types=change_types,
        )

    def _build_shared_risk_clusters(
        self,
        snapshots: list[_MonitoringSnapshot],
    ) -> list[PortfolioSharedRiskCluster]:
        factor_map: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"snapshots": [], "categories": set()}
        )
        for snapshot in snapshots:
            for factor_id, categories in self._factor_categories(snapshot.delta).items():
                bucket = factor_map[factor_id]
                bucket["snapshots"].append(snapshot)
                bucket["categories"].update(categories)

        clusters: list[PortfolioSharedRiskCluster] = []
        for factor_id, details in factor_map.items():
            cluster_snapshots: list[_MonitoringSnapshot] = details["snapshots"]
            company_ids = {snapshot.coverage.company_id for snapshot in cluster_snapshots}
            if len(company_ids) < 2:
                continue
            categories = self._sorted_change_types(details["categories"])
            label = self.context.resolve_factor_name(factor_id)
            summary = self._cluster_summary(label, cluster_snapshots)
            portfolio_items = self._segment_items(cluster_snapshots, CoverageStatus.PORTFOLIO)
            watchlist_items = self._segment_items(cluster_snapshots, CoverageStatus.WATCHLIST)
            clusters.append(
                PortfolioSharedRiskCluster(
                    factor_id=factor_id,
                    label=label,
                    summary=summary,
                    categories=categories,
                    portfolio=self._segment(
                        CoverageStatus.PORTFOLIO,
                        portfolio_items,
                    ),
                    watchlist=self._segment(
                        CoverageStatus.WATCHLIST,
                        watchlist_items,
                    ),
                )
            )

        return sorted(
            clusters,
            key=lambda cluster: (
                -(cluster.portfolio.company_count + cluster.watchlist.company_count),
                cluster.label.lower(),
            ),
        )

    def _build_change_groups(
        self,
        snapshots: list[_MonitoringSnapshot],
    ) -> list[PortfolioMonitoringChangeGroup]:
        groups: list[PortfolioMonitoringChangeGroup] = []
        for change_type in _CHANGE_ORDER:
            matching = [snapshot for snapshot in snapshots if change_type in snapshot.change_types]
            if not matching:
                continue
            portfolio_items = self._segment_items(matching, CoverageStatus.PORTFOLIO)
            watchlist_items = self._segment_items(matching, CoverageStatus.WATCHLIST)
            groups.append(
                PortfolioMonitoringChangeGroup(
                    change_type=change_type,
                    label=_CHANGE_LABELS[change_type],
                    summary=self._group_summary(change_type, portfolio_items, watchlist_items),
                    portfolio=self._segment(
                        CoverageStatus.PORTFOLIO,
                        portfolio_items,
                    ),
                    watchlist=self._segment(
                        CoverageStatus.WATCHLIST,
                        watchlist_items,
                    ),
                )
            )
        return groups

    def _build_analog_drilldown(
        self,
        snapshots: list[_MonitoringSnapshot],
    ) -> list[PortfolioAnalogDrilldown]:
        drilldown = [
            PortfolioAnalogDrilldown(
                company_id=snapshot.coverage.company_id,
                company_name=snapshot.coverage.company_name,
                coverage_status=snapshot.coverage.coverage_status,
                references=snapshot.delta.analog_references,
            )
            for snapshot in snapshots
            if snapshot.delta.analog_references
        ]
        return sorted(
            drilldown,
            key=lambda item: (-len(item.references), item.company_name.lower()),
        )

    def _change_types(self, delta: MonitoringDelta) -> list[MonitoringChangeType]:
        change_types: list[MonitoringChangeType] = []
        if delta.contradiction_references or self._has_reason_category(delta, "contradiction"):
            change_types.append(MonitoringChangeType.CONTRADICTION)
        if delta.thesis_drift_flags or self._has_reason_category(delta, "drift"):
            change_types.append(MonitoringChangeType.THESIS_DRIFT)
        if any(
            signal.state != "stable" for signal in delta.concentration_signals
        ) or self._has_reason_category(delta, "concentration"):
            change_types.append(MonitoringChangeType.CONCENTRATION)
        if not change_types and delta.changed_sections:
            change_types.append(MonitoringChangeType.SECTION_MOVEMENT)
        return change_types

    def _factor_categories(
        self,
        delta: MonitoringDelta,
    ) -> dict[str, set[MonitoringChangeType]]:
        factor_map: dict[str, set[MonitoringChangeType]] = defaultdict(set)
        for reason in delta.trigger_reasons:
            if reason.factor_id is None:
                continue
            factor_map[reason.factor_id].add(self._reason_change_type(reason.category))
        for reference in delta.contradiction_references:
            if reference.factor_id is None:
                continue
            factor_map[reference.factor_id].add(MonitoringChangeType.CONTRADICTION)
        for signal in delta.concentration_signals:
            factor_map[signal.factor_id].add(MonitoringChangeType.CONCENTRATION)
        for reference in delta.analog_references:
            if reference.factor_id is None:
                continue
            factor_map[reference.factor_id].add(MonitoringChangeType.SHARED_RISK_OVERLAP)
        return factor_map

    def _factor_ids(self, delta: MonitoringDelta) -> list[str]:
        factor_ids = set(self._factor_categories(delta))
        return sorted(factor_ids)

    def _changed_sections(
        self,
        delta: MonitoringDelta,
        *,
        label_profile: str,
    ) -> list[MonitoringSectionChange]:
        return [
            MonitoringSectionChange(
                section_id=section_id,
                label=self.context.resolve_memo_section_label(
                    section_id,
                    label_profile=label_profile,
                ),
            )
            for section_id in delta.changed_sections
        ]

    @staticmethod
    def _segment_items(
        snapshots: list[_MonitoringSnapshot],
        status: CoverageStatus,
    ) -> list[PortfolioMonitoringCompanyItem]:
        return sorted(
            [
                snapshot.item
                for snapshot in snapshots
                if snapshot.coverage.coverage_status == status
            ],
            key=lambda item: (
                PortfolioReadService._alert_sort_key(item.alert_level.value),
                -int(item.recorded_at.timestamp()),
                item.company_name.lower(),
            ),
        )

    @staticmethod
    def _segment(
        status: CoverageStatus,
        companies: list[PortfolioMonitoringCompanyItem],
    ) -> PortfolioMonitoringSegment:
        return PortfolioMonitoringSegment(
            coverage_status=status,
            company_count=len(companies),
            companies=companies,
        )

    @staticmethod
    def _alert_sort_key(alert_level: str) -> int:
        return {"high": 0, "medium": 1, "low": 2}.get(alert_level, 3)

    @staticmethod
    def _has_reason_category(delta: MonitoringDelta, category: str) -> bool:
        return any(reason.category == category for reason in delta.trigger_reasons)

    @staticmethod
    def _reason_change_type(category: str) -> MonitoringChangeType:
        if category == "contradiction":
            return MonitoringChangeType.CONTRADICTION
        if category == "drift":
            return MonitoringChangeType.THESIS_DRIFT
        if category == "concentration":
            return MonitoringChangeType.CONCENTRATION
        return MonitoringChangeType.SECTION_MOVEMENT

    @staticmethod
    def _sorted_change_types(
        categories: set[MonitoringChangeType],
    ) -> list[MonitoringChangeType]:
        ordered_values = (MonitoringChangeType.SHARED_RISK_OVERLAP, *_CHANGE_ORDER)
        order = {value: index for index, value in enumerate(ordered_values)}
        return sorted(categories, key=lambda value: order.get(value, len(order)))

    @staticmethod
    def _cluster_summary(
        label: str,
        snapshots: list[_MonitoringSnapshot],
    ) -> str:
        portfolio_count = sum(
            1
            for snapshot in snapshots
            if snapshot.coverage.coverage_status == CoverageStatus.PORTFOLIO
        )
        watchlist_count = sum(
            1
            for snapshot in snapshots
            if snapshot.coverage.coverage_status == CoverageStatus.WATCHLIST
        )
        return (
            f"{label} appears across {len(snapshots)} covered names: "
            f"{portfolio_count} portfolio and {watchlist_count} watchlist."
        )

    @staticmethod
    def _group_summary(
        change_type: MonitoringChangeType,
        portfolio_items: list[PortfolioMonitoringCompanyItem],
        watchlist_items: list[PortfolioMonitoringCompanyItem],
    ) -> str:
        label = _CHANGE_LABELS[change_type].lower()
        return (
            f"{label} currently affect {len(portfolio_items)} portfolio names "
            f"and {len(watchlist_items)} watchlist names."
        )
