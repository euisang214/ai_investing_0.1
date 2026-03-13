from __future__ import annotations

from ai_investing.application.portfolio import PortfolioReadService
from ai_investing.domain.enums import (
    AlertLevel,
    CompanyType,
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
    CoverageEntry,
    MonitoringCurrentState,
    MonitoringDelta,
    MonitoringReason,
    NotificationEvent,
    RefreshJobRecord,
    ReviewQueueEntry,
    RunRecord,
)
from ai_investing.persistence.repositories import Repository


def _save_coverage(
    repository: Repository,
    *,
    company_id: str,
    company_name: str,
    coverage_status: CoverageStatus,
) -> CoverageEntry:
    entry = CoverageEntry(
        company_id=company_id,
        company_name=company_name,
        company_type=CompanyType.PUBLIC,
        coverage_status=coverage_status,
    )
    repository.upsert_coverage(entry)
    return entry


def _save_run_and_delta(
    repository: Repository,
    *,
    company_id: str,
    run_kind: RunKind,
    change_summary: str,
    alert_level: AlertLevel,
    changed_sections: list[str],
    reason_specs: list[tuple[str, str, str]],
    thesis_drift_flags: list[str] | None = None,
    concentration_specs: list[tuple[str, str, str, str]] | None = None,
    prior_run_id: str | None = None,
) -> MonitoringDelta:
    run = RunRecord(
        company_id=company_id,
        run_kind=run_kind,
        status=RunStatus.COMPLETE,
    )
    repository.save_run(run)
    delta = MonitoringDelta(
        company_id=company_id,
        prior_run_id=prior_run_id,
        current_run_id=run.run_id,
        change_summary=change_summary,
        changed_sections=changed_sections,
        alert_level=alert_level,
        thesis_drift_flags=thesis_drift_flags or [],
        trigger_reasons=[
            MonitoringReason(
                category=category,
                summary=summary,
                factor_id=factor_id,
            )
            for category, factor_id, summary in reason_specs
        ],
        concentration_signals=[
            MonitoringCurrentState(
                category=category,
                label=label,
                factor_id=factor_id,
                state=state,
                summary=f"{label} is {state}.",
            )
            for category, factor_id, label, state in concentration_specs or []
        ],
    )
    repository.save_monitoring_delta(delta)
    return delta


def test_memory_write_read_semantics(context) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        first = ClaimCard(
            company_id="ACME",
            company_type=CompanyType.PUBLIC,
            run_id="run_old",
            panel_id="gatekeepers",
            factor_id="need_to_exist",
            agent_id="gatekeeper_advocate",
            claim="Acme appears durable on need to exist.",
            bull_case="Operationally mandatory.",
            bear_case="Could still be replaced over time.",
            confidence=0.7,
            evidence_quality=0.8,
            staleness_assessment="fresh",
            time_horizon="12 months",
            durability_horizon="multi-year",
            what_changed="Initial coverage run.",
            namespace="company/ACME/claims/need_to_exist",
        )
        repository.save_claim_cards([first])

        second = ClaimCard(
            company_id="ACME",
            company_type=CompanyType.PUBLIC,
            run_id="run_new",
            panel_id="gatekeepers",
            factor_id="need_to_exist",
            agent_id="gatekeeper_advocate",
            claim="Acme appears more fragile on need to exist.",
            bull_case="Still embedded.",
            bear_case="Replacement pressure increased.",
            confidence=0.6,
            evidence_quality=0.7,
            staleness_assessment="fresh",
            time_horizon="12 months",
            durability_horizon="multi-year",
            what_changed="Signal mix changed.",
            namespace="company/ACME/claims/need_to_exist",
        )
        repository.save_claim_cards([second])

        active = repository.list_claim_cards("ACME", active_only=True)
        all_claims = repository.list_claim_cards("ACME", active_only=False)
        assert len(active) == 1
        assert active[0].claim_id == second.claim_id
        assert len(all_claims) == 2
        assert any(claim.status.value == "superseded" for claim in all_claims)


def test_repository_lists_monitoring_history_newest_first(context) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        _save_coverage(
            repository,
            company_id="ACME",
            company_name="Acme Cloud",
            coverage_status=CoverageStatus.WATCHLIST,
        )
        first = _save_run_and_delta(
            repository,
            company_id="ACME",
            run_kind=RunKind.ANALYZE,
            change_summary="Initial monitoring state.",
            alert_level=AlertLevel.LOW,
            changed_sections=["risk"],
            reason_specs=[("drift", "balance_sheet_survivability", "Funding stayed stable.")],
        )
        second = _save_run_and_delta(
            repository,
            company_id="ACME",
            run_kind=RunKind.REFRESH,
            prior_run_id=first.current_run_id,
            change_summary="Refresh detected concentration pressure.",
            alert_level=AlertLevel.HIGH,
            changed_sections=["risk", "overall_recommendation"],
            reason_specs=[
                (
                    "concentration",
                    "customer_concentration",
                    "Customer concentration worsened.",
                )
            ],
        )

        history = repository.list_monitoring_deltas("ACME")
        limited = repository.list_monitoring_deltas("ACME", limit=1)

    assert [delta.delta_id for delta in history] == [second.delta_id, first.delta_id]
    assert [delta.delta_id for delta in limited] == [second.delta_id]


def test_repository_filters_portfolio_and_watchlist_coverage(context) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        _save_coverage(
            repository,
            company_id="ACME",
            company_name="Acme Cloud",
            coverage_status=CoverageStatus.WATCHLIST,
        )
        _save_coverage(
            repository,
            company_id="BETA",
            company_name="Beta Logistics Software",
            coverage_status=CoverageStatus.PORTFOLIO,
        )

        portfolio = repository.list_coverage(coverage_statuses=[CoverageStatus.PORTFOLIO])
        watchlist = repository.list_coverage(coverage_statuses=[CoverageStatus.WATCHLIST])

    assert [entry.company_id for entry in portfolio] == ["BETA"]
    assert [entry.company_id for entry in watchlist] == ["ACME"]


def test_portfolio_read_service_returns_monitoring_history_with_run_metadata(context) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        coverage = _save_coverage(
            repository,
            company_id="ACME",
            company_name="Acme Cloud",
            coverage_status=CoverageStatus.WATCHLIST,
        )
        first = _save_run_and_delta(
            repository,
            company_id="ACME",
            run_kind=RunKind.ANALYZE,
            change_summary="Initial coverage delta.",
            alert_level=AlertLevel.LOW,
            changed_sections=["risk"],
            reason_specs=[("drift", "balance_sheet_survivability", "Initial downside view.")],
        )
        second = _save_run_and_delta(
            repository,
            company_id="ACME",
            run_kind=RunKind.REFRESH,
            prior_run_id=first.current_run_id,
            change_summary="Refresh widened the risk view.",
            alert_level=AlertLevel.MEDIUM,
            changed_sections=["risk", "overall_recommendation"],
            reason_specs=[
                ("contradiction", "customer_concentration", "Signals now conflict."),
            ],
        )

    history = PortfolioReadService(context).get_company_monitoring_history("ACME")

    assert history.company_name == coverage.company_name
    assert history.coverage_status == CoverageStatus.WATCHLIST
    assert [entry.run_kind for entry in history.entries] == [RunKind.REFRESH, RunKind.ANALYZE]
    assert [entry.run_status for entry in history.entries] == [
        RunStatus.COMPLETE,
        RunStatus.COMPLETE,
    ]
    assert history.entries[0].run_id == second.current_run_id
    assert history.entries[0].changed_sections[0].label == context.resolve_memo_section_label(
        "risk"
    )


def test_portfolio_read_service_groups_monitoring_by_change_type_and_segment(context) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        _save_coverage(
            repository,
            company_id="ACME",
            company_name="Acme Cloud",
            coverage_status=CoverageStatus.WATCHLIST,
        )
        _save_coverage(
            repository,
            company_id="BETA",
            company_name="Beta Logistics Software",
            coverage_status=CoverageStatus.PORTFOLIO,
        )
        _save_run_and_delta(
            repository,
            company_id="ACME",
            run_kind=RunKind.REFRESH,
            change_summary="Watchlist name now shows contradictory concentration evidence.",
            alert_level=AlertLevel.HIGH,
            changed_sections=["risk", "overall_recommendation"],
            reason_specs=[
                (
                    "contradiction",
                    "customer_concentration",
                    "Signals now span positive and negative evidence.",
                ),
                (
                    "concentration",
                    "customer_concentration",
                    "A large customer now represents 12% of revenue.",
                ),
            ],
            concentration_specs=[
                (
                    "customer_dependency",
                    "customer_concentration",
                    "Customer concentration",
                    "pressured",
                )
            ],
        )
        _save_run_and_delta(
            repository,
            company_id="BETA",
            run_kind=RunKind.REFRESH,
            change_summary="Portfolio name shows overlapping concentration and drift pressure.",
            alert_level=AlertLevel.MEDIUM,
            changed_sections=["economic_spread", "growth"],
            reason_specs=[
                (
                    "drift",
                    "customer_concentration",
                    "Dependency concentration changed enough to refresh the thesis.",
                ),
                (
                    "concentration",
                    "customer_concentration",
                    "Largest customer share widened again.",
                ),
            ],
            thesis_drift_flags=["concentration_increase"],
            concentration_specs=[
                (
                    "customer_dependency",
                    "customer_concentration",
                    "Customer concentration",
                    "pressured",
                )
            ],
        )

    summary = PortfolioReadService(context).get_portfolio_monitoring_summary()
    groups = {group.change_type: group for group in summary.change_groups}

    assert summary.included_segments == [
        CoverageStatus.PORTFOLIO,
        CoverageStatus.WATCHLIST,
    ]
    assert summary.portfolio_company_count == 1
    assert summary.watchlist_company_count == 1

    cluster = summary.shared_risk_clusters[0]
    assert cluster.factor_id == "customer_concentration"
    assert cluster.portfolio.companies[0].company_id == "BETA"
    assert cluster.watchlist.companies[0].company_id == "ACME"
    assert MonitoringChangeType.CONCENTRATION in cluster.categories

    contradiction = groups[MonitoringChangeType.CONTRADICTION]
    assert contradiction.portfolio.company_count == 0
    assert contradiction.watchlist.company_count == 1
    assert contradiction.watchlist.companies[0].company_id == "ACME"

    concentration = groups[MonitoringChangeType.CONCENTRATION]
    assert concentration.portfolio.company_count == 1
    assert concentration.watchlist.company_count == 1

    thesis_drift = groups[MonitoringChangeType.THESIS_DRIFT]
    assert thesis_drift.portfolio.company_count == 1
    assert thesis_drift.watchlist.company_count == 0


def test_repository_enqueues_refresh_jobs_without_duplicate_company_work(context) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        _save_coverage(
            repository,
            company_id="ACME",
            company_name="Acme Cloud",
            coverage_status=CoverageStatus.WATCHLIST,
        )
        first = repository.enqueue_refresh_job(
            RefreshJobRecord(
                company_id="ACME",
                company_name="Acme Cloud",
                coverage_status=CoverageStatus.WATCHLIST,
                trigger=RefreshJobTrigger.SCHEDULED,
                requested_by="scheduler",
            )
        )
        second = repository.enqueue_refresh_job(
            RefreshJobRecord(
                company_id="ACME",
                company_name="Acme Cloud",
                coverage_status=CoverageStatus.WATCHLIST,
                trigger=RefreshJobTrigger.MANUAL,
                requested_by="operator",
            )
        )
        summary = repository.get_queue_summary()

    assert first.job_id == second.job_id
    assert summary.total_jobs == 1
    assert summary.active_company_count == 1
    assert summary.jobs[0].status == RefreshJobStatus.QUEUED


def test_repository_claims_marks_review_queue_and_builds_job_detail(context) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        _save_coverage(
            repository,
            company_id="ACME",
            company_name="Acme Cloud",
            coverage_status=CoverageStatus.WATCHLIST,
        )
        queued = repository.enqueue_refresh_job(
            RefreshJobRecord(
                company_id="ACME",
                company_name="Acme Cloud",
                coverage_status=CoverageStatus.WATCHLIST,
            )
        )
        claimed = repository.claim_refresh_jobs(limit=1, worker_id="worker_a")
        started = repository.start_refresh_job(
            queued.job_id,
            run_id="run_review",
            worker_id="worker_a",
        )
        review = repository.save_review_queue_entry(
            ReviewQueueEntry(
                company_id="ACME",
                company_name="Acme Cloud",
                coverage_status=CoverageStatus.WATCHLIST,
                run_id="run_review",
                job_id=started.job_id,
                next_action=ReviewNextAction.CONTINUE_PROVISIONAL,
                reason_summary="Gatekeepers failed and need operator review.",
            )
        )
        repository.mark_refresh_job_review_required(
            started.job_id,
            run_id="run_review",
            review_entry_id=review.review_id,
        )
        detail = repository.get_queue_job_detail(started.job_id)
        review_items = repository.list_review_queue_items()

    assert len(claimed) == 1
    assert claimed[0].status == RefreshJobStatus.CLAIMED
    assert detail.job.status == RefreshJobStatus.REVIEW_REQUIRED
    assert detail.review is not None
    assert detail.review.review_id == review.review_id
    assert review_items[0].next_action == ReviewNextAction.CONTINUE_PROVISIONAL
    assert review_items[0].status == ReviewStatus.OPEN


def test_repository_tracks_notification_delivery_lifecycle(context) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        event = repository.save_notification_event(
            NotificationEvent(
                category=NotificationCategory.GATEKEEPER_FAILED,
                company_id="ACME",
                company_name="Acme Cloud",
                coverage_status=CoverageStatus.WATCHLIST,
                run_id="run_review",
                job_id="job_1",
                review_id="rev_1",
                title="Gatekeeper failed for ACME",
                summary="Immediate operator review required.",
                next_action="continue_provisional",
            )
        )
        claimed = repository.claim_notification_events(limit=1, consumer_id="n8n")
        dispatched = repository.mark_notification_dispatched(event.event_id)
        acknowledged = repository.acknowledge_notification_event(event.event_id)
        items = repository.list_notification_event_items()

    assert len(claimed) == 1
    assert claimed[0].status == NotificationStatus.CLAIMED
    assert dispatched.delivery_attempts == 1
    assert acknowledged.status == NotificationStatus.ACKNOWLEDGED
    assert items[0].category == NotificationCategory.GATEKEEPER_FAILED
    assert items[0].status == NotificationStatus.ACKNOWLEDGED
