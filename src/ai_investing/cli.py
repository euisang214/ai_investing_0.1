from __future__ import annotations

import json
from pathlib import Path

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
from ai_investing.domain.enums import Cadence, CompanyType, CoverageStatus
from ai_investing.domain.models import CoverageEntry

app = typer.Typer(no_args_is_help=True)


def _context() -> AppContext:
    return AppContext.load()


@app.command("init-db")
def init_db() -> None:
    AnalysisService(_context()).initialize_database()
    typer.echo("database initialized")


@app.command("ingest-public-data")
def ingest_public_data(input_dir: Path) -> None:
    profile, evidence_ids = IngestionService(_context()).ingest_public_data(input_dir)
    typer.echo(json.dumps({"profile": profile.model_dump(mode="json"), "evidence_ids": evidence_ids}, indent=2))


@app.command("ingest-private-data")
def ingest_private_data(input_dir: Path) -> None:
    profile, evidence_ids = IngestionService(_context()).ingest_private_data(input_dir)
    typer.echo(json.dumps({"profile": profile.model_dump(mode="json"), "evidence_ids": evidence_ids}, indent=2))


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
    typer.echo(json.dumps(entry.model_dump(mode="json"), indent=2))


@app.command("analyze-company")
def analyze_company(company_id: str) -> None:
    result = AnalysisService(_context()).analyze_company(company_id)
    typer.echo(json.dumps(result, indent=2))


@app.command("run-panel")
def run_panel(company_id: str, panel_id: str) -> None:
    result = AnalysisService(_context()).run_panel(company_id, panel_id)
    typer.echo(json.dumps(result, indent=2))


@app.command("refresh-company")
def refresh_company(company_id: str) -> None:
    result = AnalysisService(_context()).refresh_company(company_id)
    typer.echo(json.dumps(result, indent=2))


@app.command("run-due-coverage")
def run_due_coverage() -> None:
    result = AnalysisService(_context()).run_due_coverage()
    typer.echo(json.dumps(result, indent=2))


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
    typer.echo(json.dumps([agent.model_dump(mode="json") for agent in agents], indent=2))


@app.command("enable-agent")
def enable_agent(agent_id: str) -> None:
    agent = AgentConfigService(_context()).enable_agent(agent_id)
    typer.echo(json.dumps(agent.model_dump(mode="json"), indent=2))


@app.command("disable-agent")
def disable_agent(agent_id: str) -> None:
    agent = AgentConfigService(_context()).disable_agent(agent_id)
    typer.echo(json.dumps(agent.model_dump(mode="json"), indent=2))


@app.command("reparent-agent")
def reparent_agent(agent_id: str, new_parent_id: str | None = None) -> None:
    agent = AgentConfigService(_context()).reparent_agent(agent_id, new_parent_id)
    typer.echo(json.dumps(agent.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    app()

