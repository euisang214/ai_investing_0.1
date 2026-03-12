from __future__ import annotations

import json

from typer.testing import CliRunner

from ai_investing.cli import app
from ai_investing.domain.enums import RunContinueAction
from ai_investing.persistence.repositories import Repository

runner = CliRunner()


def _set_panel_policy(context, company_id: str, panel_policy: str) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage(company_id)
        assert coverage is not None
        coverage.panel_policy = panel_policy
        repository.upsert_coverage(coverage)


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
