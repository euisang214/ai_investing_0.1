from __future__ import annotations

from fastapi.testclient import TestClient

from ai_investing.api.main import create_app
from ai_investing.application.services import IngestionService
from ai_investing.domain.enums import (
    AlertLevel,
    CompanyType,
    CoverageStatus,
    NotificationCategory,
    RunContinueAction,
    RunKind,
    RunStatus,
)
from ai_investing.domain.models import (
    CoverageEntry,
    EvidenceRecord,
    FactorSignal,
    MonitoringCurrentState,
    MonitoringDelta,
    MonitoringReason,
    RunRecord,
    SourceRef,
    utc_now,
)
from ai_investing.persistence.repositories import Repository
from ai_investing.providers.fake import FakeModelProvider


def _set_panel_policy(context, company_id: str, panel_policy: str) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage(company_id)
        assert coverage is not None
        coverage.panel_policy = panel_policy
        repository.upsert_coverage(coverage)


def _require_panel_context(context, panel_id: str, required_context: list[str]) -> None:
    panel = context.get_panel(panel_id)
    panel.readiness.required_context = required_context


def _seed_public_expectations_connectors(context, repo_root) -> None:
    service = IngestionService(context)
    for connector_id in (
        "acme_market_packet",
        "acme_regulatory_packet",
        "acme_transcript_news_packet",
        "acme_consensus_packet",
        "acme_events_packet",
    ):
        service.ingest_public_data(
            repo_root / "examples" / "connectors" / connector_id,
            connector_id=connector_id,
        )


def _seed_portfolio_context_peer(context, repo_root) -> None:
    IngestionService(context).ingest_private_data(repo_root / "examples" / "beta_private")
    with context.database.session() as session:
        repository = Repository(session)
        repository.upsert_coverage(
            CoverageEntry(
                company_id="BETA",
                company_name="Beta Logistics Software",
                company_type=CompanyType.PRIVATE,
                coverage_status=CoverageStatus.PORTFOLIO,
            )
        )
        run = RunRecord(
            company_id="BETA",
            run_kind=RunKind.REFRESH,
            status=RunStatus.COMPLETE,
            completed_at=utc_now(),
        )
        repository.save_run(run)
        repository.save_monitoring_delta(
            MonitoringDelta(
                company_id="BETA",
                current_run_id=run.run_id,
                change_summary="Portfolio concentration overlaps with ACME.",
                changed_sections=["risk", "overall_recommendation"],
                alert_level=AlertLevel.MEDIUM,
                trigger_reasons=[
                    MonitoringReason(
                        category="concentration",
                        factor_id="customer_concentration",
                        summary="Customer concentration overlaps with the current book.",
                    )
                ],
            )
        )


def _seed_public_overlay_evidence(context) -> None:
    records = [
        EvidenceRecord(
            company_id="ACME",
            company_type=CompanyType.PUBLIC,
            source_type="market_snapshot",
            title="Overlay valuation snapshot",
            body="Valuation, liquidity, and technical posture shape the entry.",
            source_path="examples/generated/api_overlay_valuation.json",
            namespace="company/ACME/evidence/security_overlay",
            panel_ids=["security_or_deal_overlay"],
            factor_ids=[
                "valuation_multiples_vs_peers",
                "technical_stock_movement",
                "positioning_liquidity",
            ],
            factor_signals={
                factor_id: FactorSignal(
                    stance="supported",
                    summary="Overlay evidence supports this factor.",
                )
                for factor_id in [
                    "valuation_multiples_vs_peers",
                    "technical_stock_movement",
                    "positioning_liquidity",
                ]
            },
            source_refs=[SourceRef(label="API overlay valuation")],
            evidence_quality=0.8,
            staleness_days=0,
            as_of_date=utc_now(),
            metadata={"evidence_family": "market"},
        ),
        EvidenceRecord(
            company_id="ACME",
            company_type=CompanyType.PUBLIC,
            source_type="ownership_report",
            title="Overlay ownership snapshot",
            body="Ownership, borrow, and sponsorship posture matter for implementation.",
            source_path="examples/generated/api_overlay_ownership.json",
            namespace="company/ACME/evidence/security_overlay",
            panel_ids=["security_or_deal_overlay"],
            factor_ids=[
                "insider_institutional_flow",
                "borrow_short_interest_if_relevant",
                "cap_table",
                "financing_dependency",
                "control_rights",
                "round_terms_preferences",
                "exit_path",
            ],
            factor_signals={
                factor_id: FactorSignal(
                    stance="supported",
                    summary="Overlay evidence supports this factor.",
                )
                for factor_id in [
                    "insider_institutional_flow",
                    "borrow_short_interest_if_relevant",
                    "cap_table",
                    "financing_dependency",
                    "control_rights",
                    "round_terms_preferences",
                    "exit_path",
                ]
            },
            source_refs=[SourceRef(label="API overlay ownership")],
            evidence_quality=0.79,
            staleness_days=0,
            as_of_date=utc_now(),
            metadata={"evidence_family": "ownership"},
        ),
        EvidenceRecord(
            company_id="ACME",
            company_type=CompanyType.PUBLIC,
            source_type="ownership_report",
            title="Overlay financing snapshot",
            body="Financing dependency and control rights shape the implementation posture.",
            source_path="examples/generated/api_overlay_financing.json",
            namespace="company/ACME/evidence/security_overlay",
            panel_ids=["security_or_deal_overlay"],
            factor_ids=[
                "cap_table",
                "financing_dependency",
                "control_rights",
            ],
            factor_signals={
                factor_id: FactorSignal(
                    stance="supported",
                    summary="Overlay evidence supports this factor.",
                )
                for factor_id in [
                    "cap_table",
                    "financing_dependency",
                    "control_rights",
                ]
            },
            source_refs=[SourceRef(label="API overlay financing")],
            evidence_quality=0.78,
            staleness_days=0,
            as_of_date=utc_now(),
            metadata={"evidence_family": "ownership"},
        ),
        EvidenceRecord(
            company_id="ACME",
            company_type=CompanyType.PUBLIC,
            source_type="market_commentary",
            title="Overlay exit posture",
            body="Round terms and exit path remain central to the implementation posture.",
            source_path="examples/generated/api_overlay_exit.json",
            namespace="company/ACME/evidence/security_overlay",
            panel_ids=["security_or_deal_overlay"],
            factor_ids=[
                "round_terms_preferences",
                "exit_path",
            ],
            factor_signals={
                factor_id: FactorSignal(
                    stance="supported",
                    summary="Overlay evidence supports this factor.",
                )
                for factor_id in [
                    "round_terms_preferences",
                    "exit_path",
                ]
            },
            source_refs=[SourceRef(label="API overlay exit")],
            evidence_quality=0.79,
            staleness_days=0,
            as_of_date=utc_now(),
            metadata={"evidence_family": "market"},
        ),
    ]
    with context.database.session() as session:
        Repository(session).save_evidence_records(records)


def _force_failed_gatekeeper(monkeypatch) -> None:
    original_gatekeeper_payload = FakeModelProvider._gatekeeper_payload

    def forced_fail(self, request):
        payload = original_gatekeeper_payload(self, request)
        payload["recommendation"] = "negative"
        payload["gate_decision"] = "fail"
        payload["summary"] = "Gatekeepers failed the company."
        payload["gate_reasons"] = ["Customer concentration remains too high."]
        return payload

    monkeypatch.setattr(FakeModelProvider, "_gatekeeper_payload", forced_fail)


def _save_coverage(
    repository: Repository,
    *,
    company_id: str,
    company_name: str,
    coverage_status: CoverageStatus,
) -> None:
    repository.upsert_coverage(
        CoverageEntry(
            company_id=company_id,
            company_name=company_name,
            company_type=CompanyType.PUBLIC,
            coverage_status=coverage_status,
        )
    )


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
) -> MonitoringDelta:
    run = RunRecord(
        company_id=company_id,
        run_kind=run_kind,
        status=RunStatus.COMPLETE,
    )
    repository.save_run(run)
    delta = MonitoringDelta(
        company_id=company_id,
        current_run_id=run.run_id,
        change_summary=change_summary,
        changed_sections=changed_sections,
        alert_level=alert_level,
        thesis_drift_flags=thesis_drift_flags or [],
        trigger_reasons=[
            MonitoringReason(
                category=category,
                factor_id=factor_id,
                summary=summary,
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


def _seed_monitoring_views(context) -> MonitoringDelta:
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
        acme_delta = _save_run_and_delta(
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
    return acme_delta


def test_create_app_defers_context_loading_until_startup(context, monkeypatch) -> None:
    loaded = 0

    def load_context():
        nonlocal loaded
        loaded += 1
        return context

    monkeypatch.setattr("ai_investing.api.main.AppContext.load", load_context)

    app = create_app()

    assert loaded == 0
    with TestClient(app):
        assert loaded == 1


def test_api_lifespan_initializes_database(context) -> None:
    initialize_calls = 0
    original_initialize = type(context.database).initialize

    def tracked_initialize(database) -> None:
        nonlocal initialize_calls
        if database is context.database:
            initialize_calls += 1
        original_initialize(database)

    type(context.database).initialize = tracked_initialize  # type: ignore[assignment]

    with TestClient(create_app(context)) as client:
        response = client.get("/coverage")

    type(context.database).initialize = original_initialize  # type: ignore[assignment]

    assert response.status_code == 200
    assert response.json() == {"data": []}
    assert initialize_calls == 1


def test_api_preserves_phase_one_operator_routes(context) -> None:
    app = create_app(context)
    route_paths = {route.path for route in app.routes}

    assert "/coverage" in route_paths
    assert "/cadence-policies" in route_paths
    assert "/coverage/{company_id}/disable" in route_paths
    assert "/coverage/{company_id}" in route_paths
    assert "/coverage/{company_id}/next-run-at" in route_paths
    assert "/coverage/{company_id}/schedule" in route_paths
    assert "/coverage/run-due" in route_paths
    assert "/companies/{company_id}/ingest-public" in route_paths
    assert "/companies/{company_id}/ingest-private" in route_paths
    assert "/companies/{company_id}/analyze" in route_paths
    assert "/companies/{company_id}/refresh" in route_paths
    assert "/runs/{run_id}" in route_paths
    assert "/runs/{run_id}/continue" in route_paths
    assert "/companies/{company_id}/panels/{panel_id}/run" in route_paths
    assert "/companies/{company_id}/memo" in route_paths
    assert "/companies/{company_id}/delta" in route_paths
    assert "/companies/{company_id}/monitoring-history" in route_paths
    assert "/portfolio/monitoring-summary" in route_paths
    assert "/agents" in route_paths
    assert "/agents/{agent_id}/enable" in route_paths
    assert "/agents/{agent_id}/disable" in route_paths
    assert "/agents/{agent_id}/reparent" in route_paths


def test_api_exposes_queue_worker_and_notification_routes(context) -> None:
    app = create_app(context)
    route_paths = {route.path for route in app.routes}

    assert "/queue" in route_paths
    assert "/queue/{job_id}" in route_paths
    assert "/queue/enqueue-selected" in route_paths
    assert "/queue/enqueue-watchlist" in route_paths
    assert "/queue/enqueue-portfolio" in route_paths
    assert "/queue/enqueue-due" in route_paths
    assert "/queue/{job_id}/retry" in route_paths
    assert "/queue/{job_id}/cancel" in route_paths
    assert "/queue/{job_id}/force-run" in route_paths
    assert "/review-queue" in route_paths
    assert "/workers/run" in route_paths
    assert "/notifications" in route_paths
    assert "/notifications/claim" in route_paths
    assert "/notifications/{event_id}/dispatch" in route_paths
    assert "/notifications/{event_id}/acknowledge" in route_paths
    assert "/notifications/{event_id}/fail" in route_paths


def test_api_returns_stable_not_found_error_shape(context) -> None:
    with TestClient(create_app(context)) as client:
        response = client.get("/companies/UNKNOWN/memo")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "UNKNOWN"},
    }


def test_api_coverage_lifecycle_and_agent_reparent(context) -> None:
    with TestClient(create_app(context)) as client:
        created = client.post(
            "/coverage",
            json={
                "company_id": "ACME",
                "company_name": "Acme Cloud",
                "company_type": "public",
                "coverage_status": "watchlist",
            },
        )
        assert created.status_code == 201

        updated = client.post(
            "/coverage/ACME/next-run-at",
            json={"next_run_at": "2026-03-10T09:30:00+00:00"},
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["next_run_at"] == "2026-03-10T09:30:00Z"

        disabled = client.post("/coverage/ACME/disable")
        assert disabled.status_code == 200
        assert disabled.json()["data"]["enabled"] is False

        reparented = client.post(
            "/agents/demand_skeptic/reparent",
            json={"parent_id": "gatekeeper_advocate"},
        )
        assert reparented.status_code == 200
        assert reparented.json()["data"]["parent_id"] == "gatekeeper_advocate"

        removed = client.delete("/coverage/ACME")
        assert removed.status_code == 200
        assert removed.json() == {"data": {"company_id": "ACME", "removed": True}}


def test_api_lists_cadence_policies_and_updates_schedule(context) -> None:
    with TestClient(create_app(context)) as client:
        policies = client.get("/cadence-policies")
        assert policies.status_code == 200
        payload = policies.json()["data"]
        assert payload["workspace_timezone"] == "America/New_York"
        assert payload["default_policy_id"] == "weekly"
        assert {policy["id"] for policy in payload["cadence_policies"]} >= {
            "weekly",
            "biweekly",
            "weekdays",
            "monthly",
            "custom_weekdays",
        }

        created = client.post(
            "/coverage",
            json={
                "company_id": "SCHED",
                "company_name": "Scheduled Co",
                "company_type": "public",
                "coverage_status": "watchlist",
                "schedule_policy_id": "biweekly",
                "preferred_run_time": "09:30",
            },
        )
        assert created.status_code == 201
        assert created.json()["data"]["schedule_policy_id"] == "biweekly"
        assert created.json()["data"]["preferred_run_time"] == "09:30"

        updated = client.post(
            "/coverage/SCHED/schedule",
            json={"schedule_enabled": False},
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["schedule_enabled"] is False
        assert updated.json()["data"]["cadence"] == "manual"
        assert updated.json()["data"]["next_run_at"] is None


def test_api_rejects_company_id_mismatch_on_ingest(context, repo_root) -> None:
    with TestClient(create_app(context)) as client:
        response = client.post(
            "/companies/BETA/ingest-public",
            json={"input_dir": str(repo_root / "examples" / "acme_public")},
        )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": "Path company_id BETA does not match manifest company_id ACME.",
        }
    }


def test_api_run_panel_and_run_flow(seeded_acme) -> None:
    with TestClient(create_app(seeded_acme)) as client:
        invalid = client.post("/companies/ACME/panels/demand_revenue_quality/run")

        assert invalid.status_code == 400
        assert "gatekeepers" in invalid.json()["error"]["message"]

        completed = client.post("/companies/ACME/analyze")

        assert completed.status_code == 200
        completed_payload = completed.json()["data"]
        run_id = completed_payload["run"]["run_id"]
        assert completed_payload["run"]["status"] == "complete"
        assert completed_payload["run"]["awaiting_continue"] is False
        assert completed_payload["run"]["checkpoint_panel_id"] == "gatekeepers"
        assert completed_payload["run"]["checkpoint"]["resolution_action"] == "continue"

        shown = client.get(f"/runs/{run_id}")

        assert shown.status_code == 200
        shown_payload = shown.json()["data"]
        assert shown_payload["run"]["run_id"] == run_id
        assert shown_payload["run"]["status"] == "complete"
        assert "gatekeepers" in shown_payload["panels"]
        assert "demand_revenue_quality" in shown_payload["panels"]
        assert shown_payload["memo"]["is_initial_coverage"] is True
        assert shown_payload["delta"]["prior_run_id"] is None
        shown_sections = {
            section["section_id"]: section for section in shown_payload["memo"]["sections"]
        }
        assert shown_sections["economic_spread"]["status"] == "not_advanced"


def test_api_show_run_includes_structured_skipped_panels(seeded_acme) -> None:
    _require_panel_context(seeded_acme, "demand_revenue_quality", ["portfolio_context"])

    with TestClient(create_app(seeded_acme)) as client:
        completed = client.post("/companies/ACME/analyze")
        assert completed.status_code == 200
        run_id = completed.json()["data"]["run"]["run_id"]

        shown = client.get(f"/runs/{run_id}")

    assert shown.status_code == 200
    demand = shown.json()["data"]["panels"]["demand_revenue_quality"]
    assert demand["claims"] == []
    assert demand["skip"]["reason_code"] == "missing_context"
    assert demand["skip"]["missing_context"] == ["portfolio_context"]


def test_api_internal_policy_surfaces_panel_support_and_scoped_memo(seeded_acme) -> None:
    _set_panel_policy(seeded_acme, "ACME", "internal_company_quality")

    with TestClient(create_app(seeded_acme)) as client:
        completed = client.post("/companies/ACME/analyze")
        assert completed.status_code == 200
        run_id = completed.json()["data"]["run"]["run_id"]

        shown = client.get(f"/runs/{run_id}")

    assert shown.status_code == 200
    payload = shown.json()["data"]
    assert (
        payload["panels"]["supply_product_operations"]["support"]["status"] == "supported"
    )
    assert (
        payload["panels"]["management_governance_capital_allocation"]["support"]["status"]
        == "supported"
    )
    assert (
        payload["panels"]["financial_quality_liquidity_economic_model"]["support"]["status"]
        == "supported"
    )
    sections = {section["section_id"]: section for section in payload["memo"]["sections"]}
    assert sections["durability_resilience"]["status"] == "refreshed"
    assert sections["economic_spread"]["status"] == "refreshed"
    assert sections["valuation_terms"]["status"] == "refreshed"
    assert sections["risk"]["status"] == "refreshed"
    assert sections["expectations_variant_view"]["status"] == "not_advanced"
    assert sections["portfolio_fit_positioning"]["status"] == "not_advanced"


def test_api_exposes_monitoring_history_and_portfolio_summary(context) -> None:
    acme_delta = _seed_monitoring_views(context)

    with TestClient(create_app(context)) as client:
        delta = client.get("/companies/ACME/delta")
        history = client.get("/companies/ACME/monitoring-history", params={"limit": 1})
        summary = client.get("/portfolio/monitoring-summary")
        watchlist = client.get("/portfolio/monitoring-summary", params={"segment": "watchlist"})

    assert delta.status_code == 200
    assert delta.json()["data"]["delta_id"] == acme_delta.delta_id

    assert history.status_code == 200
    history_payload = history.json()["data"]
    assert history_payload["company_id"] == "ACME"
    assert history_payload["coverage_status"] == "watchlist"
    assert len(history_payload["entries"]) == 1
    assert history_payload["entries"][0]["delta"]["delta_id"] == acme_delta.delta_id

    assert summary.status_code == 200
    summary_payload = summary.json()["data"]
    assert summary_payload["included_segments"] == ["portfolio", "watchlist"]
    assert summary_payload["portfolio_company_count"] == 1
    assert summary_payload["watchlist_company_count"] == 1
    cluster = summary_payload["shared_risk_clusters"][0]
    assert cluster["portfolio"]["companies"][0]["company_id"] == "BETA"
    assert cluster["watchlist"]["companies"][0]["company_id"] == "ACME"
    contradiction = next(
        group
        for group in summary_payload["change_groups"]
        if group["change_type"] == "contradiction"
    )
    assert contradiction["portfolio"]["company_count"] == 0
    assert contradiction["watchlist"]["company_count"] == 1

    assert watchlist.status_code == 200
    watchlist_payload = watchlist.json()["data"]
    assert watchlist_payload["included_segments"] == ["watchlist"]
    assert watchlist_payload["portfolio_company_count"] == 0
    assert watchlist_payload["watchlist_company_count"] == 1


def test_api_run_panel_rejects_scaffold_only_panel(seeded_acme) -> None:
    with TestClient(create_app(seeded_acme)) as client:
        response = client.post("/companies/ACME/panels/supply_product_operations/run")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": (
                "Runs must begin at gatekeepers. Resume an existing paused run for downstream "
                "panels."
            ),
        }
    }

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


def test_api_recommendation_scope_surfaces_company_quality_only_when_overlays_skip(
    seeded_acme,
    repo_root,
) -> None:
    _set_panel_policy(seeded_acme, "ACME", "full_surface")
    _seed_public_expectations_connectors(seeded_acme, repo_root)

    with TestClient(create_app(seeded_acme)) as client:
        response = client.post("/companies/ACME/analyze")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["overall_recommendation_scope"]["status"] == "company_quality_only"
    assert payload["overall_recommendation_scope"]["overlays"] == {
        "security_or_deal_overlay": "unsupported",
        "portfolio_fit_positioning": "unsupported",
    }
    assert (
        "company-quality-only" in payload["overall_recommendation_scope"]["summary"]
    )

    with TestClient(create_app(seeded_acme)) as client:
        shown = client.get(f"/runs/{payload['run']['run_id']}")

    assert shown.status_code == 200
    shown_payload = shown.json()["data"]
    assert shown_payload["overall_recommendation_scope"]["status"] == "company_quality_only"
    assert shown_payload["overall_recommendation_scope"]["overlays"] == {
        "security_or_deal_overlay": "unsupported",
        "portfolio_fit_positioning": "unsupported",
    }


def test_api_recommendation_scope_surfaces_overlay_complete_when_overlays_run(
    seeded_acme,
    repo_root,
) -> None:
    _set_panel_policy(seeded_acme, "ACME", "full_surface")
    _seed_public_expectations_connectors(seeded_acme, repo_root)
    _seed_public_overlay_evidence(seeded_acme)
    _seed_portfolio_context_peer(seeded_acme, repo_root)

    with TestClient(create_app(seeded_acme)) as client:
        response = client.post("/companies/ACME/analyze")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["overall_recommendation_scope"]["status"] == "overlay_complete"
    assert payload["overall_recommendation_scope"]["label"] == "Overlay-aware recommendation"
    assert payload["overall_recommendation_scope"]["overlays"] == {
        "security_or_deal_overlay": "supported",
        "portfolio_fit_positioning": "supported",
    }


def test_api_run_due_returns_paused_run_payload(seeded_acme, monkeypatch) -> None:
    _force_failed_gatekeeper(monkeypatch)
    with TestClient(create_app(seeded_acme)) as client:
        first = client.post("/coverage/run-due")

        assert first.status_code == 200
        first_payload = first.json()["data"]
        first_run_id = first_payload[0]["run"]["run_id"]
        assert first_payload[0]["run"]["status"] == "awaiting_continue"
        assert first_payload[0]["run"]["awaiting_continue"] is True

        second = client.post("/coverage/run-due")

        assert second.status_code == 200
        second_payload = second.json()["data"]
        assert second_payload[0]["run"]["run_id"] == first_run_id
        assert second_payload[0]["run"]["checkpoint"]["allowed_actions"] == [
            "stop",
            "continue_provisional",
        ]


def test_api_enqueue_worker_and_notification_flow(seeded_acme) -> None:
    with TestClient(create_app(seeded_acme)) as client:
        enqueued = client.post(
            "/queue/enqueue-selected",
            json={"company_ids": ["ACME"], "requested_by": "operator"},
        )
        assert enqueued.status_code == 200
        jobs = enqueued.json()["data"]
        assert len(jobs) == 1
        job_id = jobs[0]["job_id"]

        summary = client.get("/queue")
        assert summary.status_code == 200
        assert summary.json()["data"]["total_jobs"] == 1

        detail = client.get(f"/queue/{job_id}")
        assert detail.status_code == 200
        assert detail.json()["data"]["job"]["company_id"] == "ACME"

        worked = client.post(
            "/workers/run",
            json={"limit": 1, "worker_id": "worker_a", "max_concurrency": 1},
        )
        assert worked.status_code == 200
        assert worked.json()["data"][0]["run"]["status"] == "complete"

        notifications = client.get("/notifications")
        assert notifications.status_code == 200
        categories = {
            item["category"] for item in notifications.json()["data"]
        }
        assert categories == {"material_change", "daily_digest"}

        claimed = client.post(
            "/notifications/claim",
            json={"limit": 1, "consumer_id": "n8n"},
        )
        assert claimed.status_code == 200
        event_id = claimed.json()["data"][0]["event_id"]

        dispatched = client.post(f"/notifications/{event_id}/dispatch")
        assert dispatched.status_code == 200

        acknowledged = client.post(f"/notifications/{event_id}/acknowledge")
        assert acknowledged.status_code == 200
        assert acknowledged.json()["data"]["status"] == "acknowledged"


def test_api_worker_failed_gatekeeper_surfaces_review_queue(seeded_acme, monkeypatch) -> None:
    _force_failed_gatekeeper(monkeypatch)

    with TestClient(create_app(seeded_acme)) as client:
        enqueued = client.post(
            "/queue/enqueue-selected",
            json={"company_ids": ["ACME"], "requested_by": "operator"},
        )
        job_id = enqueued.json()["data"][0]["job_id"]

        worked = client.post(
            "/workers/run",
            json={"limit": 1, "worker_id": "worker_b", "max_concurrency": 1},
        )
        assert worked.status_code == 200
        assert worked.json()["data"][0]["run"]["status"] == "awaiting_continue"

        review = client.get("/review-queue")
        assert review.status_code == 200
        assert review.json()["data"][0]["company_id"] == "ACME"

        detail = client.get(f"/queue/{job_id}")
        assert detail.status_code == 200
        assert detail.json()["data"]["job"]["status"] == "review_required"

        notifications = client.get("/notifications")
        assert NotificationCategory.GATEKEEPER_FAILED.value in {
            item["category"] for item in notifications.json()["data"]
        }


def test_api_continue_run_accepts_provisional_action(context, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_continue_run(_service, run_id: str, action: RunContinueAction) -> dict[str, object]:
        captured["run_id"] = run_id
        captured["action"] = action
        return {
            "run": {
                "run_id": run_id,
                "company_id": "ACME",
                "run_kind": "analyze",
                "status": "provisional",
                "triggered_by": "system",
                "panel_id": None,
                "started_at": "2026-03-11T00:00:00Z",
                "completed_at": "2026-03-11T00:05:00Z",
                "gate_decision": "fail",
                "awaiting_continue": False,
                "gated_out": False,
                "provisional": True,
                "stopped_after_panel": None,
                "checkpoint_panel_id": "gatekeepers",
                "checkpoint": {
                    "checkpoint_panel_id": "gatekeepers",
                    "allowed_actions": ["stop", "continue_provisional"],
                    "provisional_required": True,
                    "note": "Gatekeepers failed. Continue only as provisional downstream analysis.",
                    "requested_at": "2026-03-11T00:00:00Z",
                    "resolved_at": "2026-03-11T00:05:00Z",
                    "resolution_action": "continue_provisional",
                },
                "metadata": {
                    "panel_ids": ["gatekeepers", "demand_revenue_quality"],
                },
            },
            "panels": {},
            "memo": None,
            "delta": None,
        }

    monkeypatch.setattr("ai_investing.api.main.AnalysisService.continue_run", fake_continue_run)

    with TestClient(create_app(context)) as client:
        response = client.post(
            "/runs/run_failed/continue",
            json={"action": "continue_provisional"},
        )

    assert response.status_code == 200
    assert captured == {
        "run_id": "run_failed",
        "action": RunContinueAction.CONTINUE_PROVISIONAL,
    }
    assert response.json()["data"]["run"]["provisional"] is True


def test_api_notification_failure_reporting(seeded_acme) -> None:
    with TestClient(create_app(seeded_acme)) as client:
        enqueued = client.post(
            "/queue/enqueue-selected",
            json={"company_ids": ["ACME"], "requested_by": "operator"},
        )
        assert enqueued.status_code == 200

        worked = client.post(
            "/workers/run",
            json={"limit": 1, "worker_id": "worker_fail_test", "max_concurrency": 1},
        )
        assert worked.status_code == 200

        claimed = client.post(
            "/notifications/claim",
            json={"limit": 1, "consumer_id": "n8n"},
        )
        assert claimed.status_code == 200
        event_id = claimed.json()["data"][0]["event_id"]

        dispatched = client.post(f"/notifications/{event_id}/dispatch")
        assert dispatched.status_code == 200

        failed = client.post(
            f"/notifications/{event_id}/fail",
            json={"error_message": "SMTP connection refused"},
        )
        assert failed.status_code == 200
        assert failed.json()["data"]["status"] == "failed"
        assert failed.json()["data"]["last_error"] == "SMTP connection refused"

