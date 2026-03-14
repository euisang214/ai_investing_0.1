from __future__ import annotations

import json

from typer.testing import CliRunner

from ai_investing.cli import app
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
    MonitoringCurrentState,
    MonitoringDelta,
    MonitoringReason,
    RunRecord,
)
from ai_investing.persistence.repositories import Repository
from ai_investing.providers.fake import FakeModelProvider

runner = CliRunner()


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


def test_cli_coverage_lifecycle_commands(context, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: context)

    add_result = runner.invoke(
        app,
        ["add-coverage", "ACME", "Acme Cloud", "public", "watchlist"],
    )
    assert add_result.exit_code == 0

    list_result = runner.invoke(app, ["list-coverage"])
    assert list_result.exit_code == 0
    listed = json.loads(list_result.stdout)
    assert listed[0]["company_id"] == "ACME"

    next_run_result = runner.invoke(
        app,
        ["set-next-run-at", "ACME", "2026-03-10T09:30:00+00:00"],
    )
    assert next_run_result.exit_code == 0
    assert json.loads(next_run_result.stdout)["next_run_at"] == "2026-03-10T09:30:00Z"

    disable_result = runner.invoke(app, ["disable-coverage", "ACME"])
    assert disable_result.exit_code == 0
    assert json.loads(disable_result.stdout)["enabled"] is False

    remove_result = runner.invoke(app, ["remove-coverage", "ACME"])
    assert remove_result.exit_code == 0
    assert json.loads(remove_result.stdout) == {"company_id": "ACME", "removed": True}


def test_cli_lists_cadence_policies_and_updates_schedule(context, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: context)

    policies = runner.invoke(app, ["list-cadence-policies"])
    assert policies.exit_code == 0
    payload = json.loads(policies.stdout)
    assert payload["workspace_timezone"] == "America/New_York"
    assert {policy["id"] for policy in payload["cadence_policies"]} >= {
        "weekly",
        "biweekly",
        "weekdays",
        "monthly",
        "custom_weekdays",
    }

    created = runner.invoke(
        app,
        [
            "add-coverage",
            "SCHED",
            "Scheduled Co",
            "public",
            "watchlist",
            "--schedule-policy-id",
            "biweekly",
            "--preferred-run-time",
            "09:30",
        ],
    )
    assert created.exit_code == 0
    created_payload = json.loads(created.stdout)
    assert created_payload["schedule_policy_id"] == "biweekly"
    assert created_payload["preferred_run_time"] == "09:30"

    disabled = runner.invoke(
        app,
        ["set-coverage-schedule", "SCHED", "--schedule-disabled"],
    )
    assert disabled.exit_code == 0
    disabled_payload = json.loads(disabled.stdout)
    assert disabled_payload["schedule_enabled"] is False
    assert disabled_payload["cadence"] == "manual"
    assert disabled_payload["next_run_at"] is None


def test_cli_reparent_agent_command(context, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: context)

    result = runner.invoke(
        app,
        ["reparent-agent", "demand_skeptic", "gatekeeper_advocate"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["parent_id"] == "gatekeeper_advocate"


def test_cli_run_panel_and_run_flow(seeded_acme, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)

    invalid = runner.invoke(app, ["run-panel", "ACME", "demand_revenue_quality"])

    assert invalid.exit_code != 0
    assert invalid.exception is not None
    assert "gatekeepers" in str(invalid.exception)

    completed = runner.invoke(app, ["analyze-company", "ACME"])

    assert completed.exit_code == 0
    completed_payload = json.loads(completed.stdout)
    run_id = completed_payload["run"]["run_id"]
    assert completed_payload["run"]["status"] == "complete"
    assert completed_payload["run"]["checkpoint"]["resolution_action"] == "continue"

    shown = runner.invoke(app, ["show-run", run_id])

    assert shown.exit_code == 0
    shown_payload = json.loads(shown.stdout)
    assert shown_payload["run"]["run_id"] == run_id
    assert shown_payload["run"]["status"] == "complete"
    assert shown_payload["memo"]["is_initial_coverage"] is True
    assert shown_payload["delta"]["prior_run_id"] is None
    shown_sections = {
        section["section_id"]: section for section in shown_payload["memo"]["sections"]
    }
    assert shown_sections["economic_spread"]["status"] == "not_advanced"


def test_cli_show_run_includes_structured_skipped_panels(seeded_acme, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)
    _require_panel_context(seeded_acme, "demand_revenue_quality", ["portfolio_context"])

    completed = runner.invoke(app, ["analyze-company", "ACME"])
    assert completed.exit_code == 0
    run_id = json.loads(completed.stdout)["run"]["run_id"]

    shown = runner.invoke(app, ["show-run", run_id])

    assert shown.exit_code == 0
    demand = json.loads(shown.stdout)["panels"]["demand_revenue_quality"]
    assert demand["claims"] == []
    assert demand["skip"]["reason_code"] == "missing_context"
    assert demand["skip"]["missing_context"] == ["portfolio_context"]


def test_cli_internal_policy_surfaces_panel_support_and_scoped_memo(
    seeded_acme,
    monkeypatch,
) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)
    _set_panel_policy(seeded_acme, "ACME", "internal_company_quality")

    completed = runner.invoke(app, ["analyze-company", "ACME"])
    assert completed.exit_code == 0
    run_id = json.loads(completed.stdout)["run"]["run_id"]

    shown = runner.invoke(app, ["show-run", run_id])

    assert shown.exit_code == 0
    payload = json.loads(shown.stdout)
    assert payload["panels"]["supply_product_operations"]["support"]["status"] == "supported"
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


def test_cli_run_panel_rejects_scaffold_only_panel(seeded_acme, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)

    invalid = runner.invoke(app, ["run-panel", "ACME", "supply_product_operations"])

    assert invalid.exit_code != 0
    assert invalid.exception is not None
    assert str(invalid.exception) == (
        "Runs must begin at gatekeepers. Resume an existing paused run for downstream panels."
    )

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


def test_cli_analyze_company_rejects_full_surface_policy(seeded_acme, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)
    _set_panel_policy(seeded_acme, "ACME", "full_surface")

    invalid = runner.invoke(app, ["analyze-company", "ACME"])

    assert invalid.exit_code != 0
    assert invalid.exception is not None
    assert str(invalid.exception) == (
        "Panel expectations_catalyst_realization is not implemented for policy full_surface."
    )

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


def test_cli_show_run_returns_persisted_checkpoint_state(seeded_acme, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)

    completed = runner.invoke(app, ["analyze-company", "ACME"])
    run_id = json.loads(completed.stdout)["run"]["run_id"]

    shown = runner.invoke(app, ["show-run", run_id])

    assert shown.exit_code == 0
    shown_payload = json.loads(shown.stdout)
    assert shown_payload["run"]["run_id"] == run_id
    assert shown_payload["run"]["status"] == "complete"
    assert shown_payload["run"]["awaiting_continue"] is False
    assert shown_payload["run"]["checkpoint_panel_id"] == "gatekeepers"
    assert shown_payload["run"]["checkpoint"]["resolution_action"] == "continue"
    assert "gatekeepers" in shown_payload["panels"]
    assert "demand_revenue_quality" in shown_payload["panels"]
    assert shown_payload["delta"] is not None


def test_cli_shows_monitoring_history_and_portfolio_summary(context, monkeypatch) -> None:
    acme_delta = _seed_monitoring_views(context)
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: context)

    delta = runner.invoke(app, ["show-delta", "ACME"])
    history = runner.invoke(app, ["show-monitoring-history", "ACME", "--limit", "1"])
    summary = runner.invoke(app, ["show-portfolio-summary"])
    portfolio = runner.invoke(app, ["show-portfolio-summary", "--segment", "portfolio"])

    assert delta.exit_code == 0
    assert json.loads(delta.stdout)["delta_id"] == acme_delta.delta_id

    assert history.exit_code == 0
    history_payload = json.loads(history.stdout)
    assert history_payload["company_id"] == "ACME"
    assert len(history_payload["entries"]) == 1
    assert history_payload["entries"][0]["delta"]["delta_id"] == acme_delta.delta_id

    assert summary.exit_code == 0
    summary_payload = json.loads(summary.stdout)
    assert summary_payload["included_segments"] == ["portfolio", "watchlist"]
    cluster = summary_payload["shared_risk_clusters"][0]
    assert cluster["portfolio"]["companies"][0]["company_id"] == "BETA"
    assert cluster["watchlist"]["companies"][0]["company_id"] == "ACME"

    assert portfolio.exit_code == 0
    portfolio_payload = json.loads(portfolio.stdout)
    assert portfolio_payload["included_segments"] == ["portfolio"]
    assert portfolio_payload["portfolio_company_count"] == 1
    assert portfolio_payload["watchlist_company_count"] == 0


def test_cli_continue_run_supports_provisional_flag(context, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: context)
    captured: dict[str, object] = {}

    def fake_continue_run(_service, run_id: str, action: RunContinueAction) -> dict[str, object]:
        captured["run_id"] = run_id
        captured["action"] = action
        return {
            "run": {
                "run_id": run_id,
                "status": "provisional",
                "awaiting_continue": False,
                "gated_out": False,
                "provisional": True,
                "stopped_after_panel": None,
                "checkpoint_panel_id": "gatekeepers",
            },
            "panels": {},
            "memo": None,
            "delta": None,
        }

    monkeypatch.setattr("ai_investing.cli.AnalysisService.continue_run", fake_continue_run)

    result = runner.invoke(app, ["continue-run", "run_test", "--provisional"])

    assert result.exit_code == 0
    assert captured == {
        "run_id": "run_test",
        "action": RunContinueAction.CONTINUE_PROVISIONAL,
    }
    assert json.loads(result.stdout)["run"]["provisional"] is True


def test_cli_enqueue_worker_and_notification_commands(seeded_acme, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)

    enqueued = runner.invoke(app, ["enqueue-companies", "ACME"])
    assert enqueued.exit_code == 0
    jobs = json.loads(enqueued.stdout)
    assert len(jobs) == 1
    job_id = jobs[0]["job_id"]

    summary = runner.invoke(app, ["queue-summary"])
    assert summary.exit_code == 0
    assert json.loads(summary.stdout)["total_jobs"] == 1

    detail = runner.invoke(app, ["show-job", job_id])
    assert detail.exit_code == 0
    assert json.loads(detail.stdout)["job"]["company_id"] == "ACME"

    worked = runner.invoke(
        app,
        ["run-worker", "--limit", "1", "--worker-id", "worker_a", "--max-concurrency", "1"],
    )
    assert worked.exit_code == 0
    assert json.loads(worked.stdout)[0]["run"]["status"] == "complete"

    notifications = runner.invoke(app, ["list-notifications"])
    assert notifications.exit_code == 0
    categories = {item["category"] for item in json.loads(notifications.stdout)}
    assert categories == {"material_change", "daily_digest"}

    claimed = runner.invoke(app, ["claim-notifications", "--consumer-id", "n8n", "--limit", "1"])
    assert claimed.exit_code == 0
    event_id = json.loads(claimed.stdout)[0]["event_id"]

    dispatched = runner.invoke(app, ["dispatch-notification", event_id])
    assert dispatched.exit_code == 0

    acknowledged = runner.invoke(app, ["acknowledge-notification", event_id])
    assert acknowledged.exit_code == 0
    assert json.loads(acknowledged.stdout)["status"] == "acknowledged"


def test_cli_enqueue_worker_failed_gatekeeper_lists_review_queue(
    seeded_acme,
    monkeypatch,
) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)
    _force_failed_gatekeeper(monkeypatch)

    enqueued = runner.invoke(app, ["enqueue-companies", "ACME"])
    assert enqueued.exit_code == 0
    job_id = json.loads(enqueued.stdout)[0]["job_id"]

    worked = runner.invoke(
        app,
        ["run-worker", "--limit", "1", "--worker-id", "worker_b", "--max-concurrency", "1"],
    )
    assert worked.exit_code == 0
    assert json.loads(worked.stdout)[0]["run"]["status"] == "awaiting_continue"

    review = runner.invoke(app, ["list-review-queue"])
    assert review.exit_code == 0
    assert json.loads(review.stdout)[0]["company_id"] == "ACME"

    detail = runner.invoke(app, ["show-job", job_id])
    assert detail.exit_code == 0
    assert json.loads(detail.stdout)["job"]["status"] == "review_required"

    notifications = runner.invoke(app, ["list-notifications"])
    assert notifications.exit_code == 0
    assert NotificationCategory.GATEKEEPER_FAILED.value in {
        item["category"] for item in json.loads(notifications.stdout)
    }
