from __future__ import annotations

import json

from typer.testing import CliRunner

from ai_investing.cli import app
from ai_investing.domain.enums import (
    AlertLevel,
    CompanyType,
    CoverageStatus,
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

runner = CliRunner()


def _set_panel_policy(context, company_id: str, panel_policy: str) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage(company_id)
        assert coverage is not None
        coverage.panel_policy = panel_policy
        repository.upsert_coverage(coverage)


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


def test_cli_reparent_agent_command(context, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: context)

    result = runner.invoke(
        app,
        ["reparent-agent", "demand_skeptic", "gatekeeper_advocate"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["parent_id"] == "gatekeeper_advocate"


def test_cli_run_panel_and_continue_flow(seeded_acme, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)

    invalid = runner.invoke(app, ["run-panel", "ACME", "demand_revenue_quality"])

    assert invalid.exit_code != 0
    assert invalid.exception is not None
    assert "gatekeepers" in str(invalid.exception)

    paused = runner.invoke(app, ["analyze-company", "ACME"])

    assert paused.exit_code == 0
    paused_payload = json.loads(paused.stdout)
    run_id = paused_payload["run"]["run_id"]
    assert paused_payload["run"]["status"] == "awaiting_continue"

    resumed = runner.invoke(app, ["continue-run", run_id, "--action", "continue"])

    assert resumed.exit_code == 0
    resumed_payload = json.loads(resumed.stdout)
    assert resumed_payload["run"]["run_id"] == run_id
    assert resumed_payload["run"]["status"] == "complete"
    assert resumed_payload["memo"]["is_initial_coverage"] is True
    assert resumed_payload["delta"]["prior_run_id"] is None
    resumed_sections = {
        section["section_id"]: section for section in resumed_payload["memo"]["sections"]
    }
    assert resumed_sections["economic_spread"]["status"] == "not_advanced"


def test_cli_run_panel_rejects_scaffold_only_panel(seeded_acme, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)

    invalid = runner.invoke(app, ["run-panel", "ACME", "supply_product_operations"])

    assert invalid.exit_code != 0
    assert invalid.exception is not None
    assert str(invalid.exception) == (
        "Panel supply_product_operations is not implemented for policy weekly_default."
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
        "Panel supply_product_operations is not implemented for policy full_surface."
    )

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


def test_cli_show_run_returns_persisted_checkpoint_state(seeded_acme, monkeypatch) -> None:
    monkeypatch.setattr("ai_investing.cli.AppContext.load", lambda: seeded_acme)

    paused = runner.invoke(app, ["analyze-company", "ACME"])
    run_id = json.loads(paused.stdout)["run"]["run_id"]

    shown = runner.invoke(app, ["show-run", run_id])

    assert shown.exit_code == 0
    shown_payload = json.loads(shown.stdout)
    assert shown_payload["run"]["run_id"] == run_id
    assert shown_payload["run"]["status"] == "awaiting_continue"
    assert shown_payload["run"]["awaiting_continue"] is True
    assert shown_payload["run"]["checkpoint_panel_id"] == "gatekeepers"
    assert shown_payload["run"]["checkpoint"]["allowed_actions"] == ["stop", "continue"]
    assert "gatekeepers" in shown_payload["panels"]
    assert shown_payload["delta"] is None


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
