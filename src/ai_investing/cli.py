from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from ai_investing.application.context import AppContext
from ai_investing.application.services import (
    AgentConfigService,
    AnalysisService,
    CoverageService,
    IngestionService,
    render_delta_json,
    render_memo_markdown,
)
from ai_investing.domain.enums import Cadence, CompanyType, CoverageStatus, RunContinueAction
from ai_investing.domain.models import CoverageEntry
from ai_investing.persistence.repositories import Repository

app = typer.Typer(no_args_is_help=True)


def _context() -> AppContext:
    return AppContext.load()


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise typer.BadParameter(
            "Use an ISO-8601 timestamp, for example 2026-03-10T09:30:00+00:00."
        ) from exc


def _emit_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, indent=2))


def _resolve_continue_action(
    *,
    action: RunContinueAction | None,
    stop: bool,
    provisional: bool,
) -> RunContinueAction:
    if stop and provisional:
        raise typer.BadParameter("Use only one of --stop or --provisional.")
    if action is not None and (stop or provisional):
        raise typer.BadParameter("Use either --action or --stop/--provisional, not both.")
    if stop:
        return RunContinueAction.STOP
    if provisional:
        return RunContinueAction.CONTINUE_PROVISIONAL
    return action or RunContinueAction.CONTINUE


def _load_run_result(context: AppContext, run_id: str) -> dict[str, Any]:
    with context.database.session() as session:
        repository = Repository(session)
        run = repository.get_run(run_id)
        if run is None:
            raise KeyError(run_id)

        claims_by_panel: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for claim in repository.list_claim_cards(run.company_id, run_id=run.run_id):
            claims_by_panel[claim.panel_id].append(claim.model_dump(mode="json"))

        panels: dict[str, dict[str, Any]] = {}
        for verdict in repository.list_panel_verdicts(run.company_id, run_id=run.run_id):
            panels[verdict.panel_id] = {
                "claims": claims_by_panel.get(verdict.panel_id, []),
                "verdict": verdict.model_dump(mode="json"),
            }

        memo = repository.get_memo_for_run(run.company_id, run.run_id)
        delta = repository.get_latest_monitoring_delta(run.company_id, run_id=run.run_id)

    return {
        "run": run.model_dump(mode="json"),
        "panels": panels,
        "memo": memo.model_dump(mode="json") if memo is not None else None,
        "delta": delta.model_dump(mode="json") if delta is not None else None,
    }


@app.command("init-db")
def init_db() -> None:
    AnalysisService(_context()).initialize_database()
    typer.echo("database initialized")


@app.command("ingest-public-data")
def ingest_public_data(input_dir: Path) -> None:
    profile, evidence_ids = IngestionService(_context()).ingest_public_data(input_dir)
    _emit_json({"profile": profile.model_dump(mode="json"), "evidence_ids": evidence_ids})


@app.command("ingest-private-data")
def ingest_private_data(input_dir: Path) -> None:
    profile, evidence_ids = IngestionService(_context()).ingest_private_data(input_dir)
    _emit_json({"profile": profile.model_dump(mode="json"), "evidence_ids": evidence_ids})


@app.command("add-coverage")
def add_coverage(
    company_id: str,
    company_name: str,
    company_type: CompanyType,
    status: CoverageStatus,
    cadence: Cadence = Cadence.WEEKLY,
    panel_policy: str = "weekly_default",
    memo_label_profile: str = "default",
    notes: str | None = None,
) -> None:
    entry = CoverageService(_context()).add_coverage(
        CoverageEntry(
            company_id=company_id,
            company_name=company_name,
            company_type=company_type,
            coverage_status=status,
            cadence=cadence,
            panel_policy=panel_policy,
            memo_label_profile=memo_label_profile,
            notes=notes,
        )
    )
    _emit_json(entry.model_dump(mode="json"))


@app.command("list-coverage")
def list_coverage() -> None:
    entries = CoverageService(_context()).list_coverage()
    _emit_json([entry.model_dump(mode="json") for entry in entries])


@app.command("disable-coverage")
def disable_coverage(company_id: str) -> None:
    entry = CoverageService(_context()).disable_coverage(company_id)
    _emit_json(entry.model_dump(mode="json"))


@app.command("remove-coverage")
def remove_coverage(company_id: str) -> None:
    CoverageService(_context()).remove_coverage(company_id)
    _emit_json({"company_id": company_id, "removed": True})


@app.command("set-next-run-at")
def set_next_run_at(
    company_id: str,
    next_run_at: str | None = typer.Argument(default=None),
) -> None:
    parsed_value = _parse_datetime(next_run_at) if next_run_at is not None else None
    entry = CoverageService(_context()).set_next_run_at(company_id, parsed_value)
    _emit_json(entry.model_dump(mode="json"))


@app.command("analyze-company")
def analyze_company(company_id: str) -> None:
    result = AnalysisService(_context()).analyze_company(company_id)
    _emit_json(result)


@app.command("run-panel")
def run_panel(company_id: str, panel_id: str) -> None:
    result = AnalysisService(_context()).run_panel(company_id, panel_id)
    _emit_json(result)


@app.command("refresh-company")
def refresh_company(company_id: str) -> None:
    result = AnalysisService(_context()).refresh_company(company_id)
    _emit_json(result)


@app.command("show-run")
def show_run(run_id: str) -> None:
    _emit_json(_load_run_result(_context(), run_id))


@app.command("continue-run")
def continue_run(
    run_id: str,
    action: Annotated[RunContinueAction | None, typer.Option("--action")] = None,
    stop: Annotated[bool, typer.Option("--stop")] = False,
    provisional: Annotated[bool, typer.Option("--provisional")] = False,
) -> None:
    resolved_action = _resolve_continue_action(
        action=action,
        stop=stop,
        provisional=provisional,
    )
    result = AnalysisService(_context()).continue_run(run_id, action=resolved_action)
    _emit_json(result)


@app.command("run-due-coverage")
def run_due_coverage() -> None:
    result = AnalysisService(_context()).run_due_coverage()
    _emit_json(result)


@app.command("generate-memo")
def generate_memo(company_id: str) -> None:
    memo = AnalysisService(_context()).generate_memo(company_id)
    typer.echo(render_memo_markdown(memo))


@app.command("show-delta")
def show_delta(company_id: str) -> None:
    delta = AnalysisService(_context()).show_delta(company_id)
    typer.echo(render_delta_json(delta))


@app.command("list-agents")
def list_agents() -> None:
    agents = AgentConfigService(_context()).list_agents()
    _emit_json([agent.model_dump(mode="json") for agent in agents])


@app.command("enable-agent")
def enable_agent(agent_id: str) -> None:
    agent = AgentConfigService(_context()).enable_agent(agent_id)
    _emit_json(agent.model_dump(mode="json"))


@app.command("disable-agent")
def disable_agent(agent_id: str) -> None:
    agent = AgentConfigService(_context()).disable_agent(agent_id)
    _emit_json(agent.model_dump(mode="json"))


@app.command("reparent-agent")
def reparent_agent(
    agent_id: str,
    new_parent_id: str | None = typer.Argument(default=None),
) -> None:
    agent = AgentConfigService(_context()).reparent_agent(agent_id, new_parent_id)
    _emit_json(agent.model_dump(mode="json"))


if __name__ == "__main__":
    app()
