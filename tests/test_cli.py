from __future__ import annotations

import json

from typer.testing import CliRunner

from ai_investing.cli import app

runner = CliRunner()


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
