from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from ai_investing.application.context import AppContext
from ai_investing.application.notifications import NotificationService
from ai_investing.application.portfolio import PortfolioReadService, resolve_summary_segments
from ai_investing.application.queue import QueueService
from ai_investing.application.services import (
    AgentConfigService,
    AnalysisService,
    CoverageService,
    IngestionService,
    render_delta_json,
    render_memo_markdown,
)
from ai_investing.application.worker import WorkerService
from ai_investing.domain.enums import Cadence, CompanyType, CoverageStatus, RunContinueAction
from ai_investing.domain.models import CoverageEntry
from ai_investing.domain.read_models import PanelRunRead
from ai_investing.persistence.repositories import Repository

app = typer.Typer(no_args_is_help=True)
_OVERLAY_PANEL_LABELS = {
    "security_or_deal_overlay": "security or deal overlay",
    "portfolio_fit_positioning": "portfolio fit positioning",
}


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


def _resolve_summary_segment_option(segment: str) -> tuple[CoverageStatus, ...]:
    try:
        return resolve_summary_segments(segment)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


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


def _attach_recommendation_scope(result: dict[str, Any]) -> dict[str, Any]:
    return {
        **result,
        "overall_recommendation_scope": _recommendation_scope(result),
    }


def _field_value(payload: Any, field_name: str) -> Any:
    if isinstance(payload, dict):
        return payload.get(field_name)
    return getattr(payload, field_name, None)


def _overlay_support_state(panel: Any) -> str:
    support = _field_value(panel, "support")
    support_status = _field_value(support, "status")
    if support_status == "supported":
        return "supported"
    if _field_value(panel, "skip") is not None or support_status == "unsupported":
        return "unsupported"
    return "pending"


def _recommendation_scope(result: dict[str, Any]) -> dict[str, Any]:
    panels = result.get("panels", {})
    overlays: dict[str, str] = {}
    pending: list[str] = []
    unsupported: list[str] = []
    for panel_id, label in _OVERLAY_PANEL_LABELS.items():
        panel = panels.get(panel_id) if isinstance(panels, dict) else None
        overlay_state = _overlay_support_state(panel)
        overlays[panel_id] = overlay_state
        if overlay_state == "supported":
            continue
        if overlay_state == "unsupported":
            unsupported.append(label)
            continue
        pending.append(label)

    if overlays and all(status == "supported" for status in overlays.values()):
        return {
            "status": "overlay_complete",
            "label": "Overlay-aware recommendation",
            "summary": (
                "Overall recommendation includes both the security or deal overlay "
                "and the portfolio fit positioning overlay."
            ),
            "overlays": overlays,
        }

    reasons: list[str] = []
    if pending:
        reasons.append(f"pending for this rollout: {', '.join(sorted(set(pending)))}")
    if unsupported:
        reasons.append(f"unsupported for this run: {', '.join(sorted(set(unsupported)))}")
    reason_text = "; ".join(reasons) if reasons else "overlay coverage is incomplete"
    return {
        "status": "company_quality_only",
        "label": "Company-quality-only recommendation",
        "summary": f"Overall recommendation remains company-quality-only because {reason_text}.",
        "overlays": overlays,
    }


def _load_run_result(context: AppContext, run_id: str) -> dict[str, Any]:
    with context.database.session() as session:
        repository = Repository(session)
        run = repository.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        support_by_panel = {
            item["panel_id"]: item
            for item in run.metadata.get("panel_support_assessments", [])
            if isinstance(item, dict) and isinstance(item.get("panel_id"), str)
        }

        claims_by_panel: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for claim in repository.list_claim_cards(run.company_id, run_id=run.run_id):
            claims_by_panel[claim.panel_id].append(claim.model_dump(mode="json"))

        panels: dict[str, dict[str, Any]] = {}
        for item in run.metadata.get("skipped_panels", []):
            panel_id = str(item.get("panel_id"))
            skip = PanelRunRead(skip=item, support=support_by_panel.get(panel_id))
            panels[str(skip.skip.panel_id)] = skip.model_dump(mode="json")
        for verdict in repository.list_panel_verdicts(run.company_id, run_id=run.run_id):
            panels[verdict.panel_id] = PanelRunRead(
                claims=claims_by_panel.get(verdict.panel_id, []),
                verdict=verdict.model_dump(mode="json"),
                support=support_by_panel.get(verdict.panel_id),
            ).model_dump(mode="json")

        memo = repository.get_memo_for_run(run.company_id, run.run_id)
        delta = repository.get_latest_monitoring_delta(run.company_id, run_id=run.run_id)

    return _attach_recommendation_scope(
        {
            "run": run.model_dump(mode="json"),
            "panels": panels,
            "memo": memo.model_dump(mode="json") if memo is not None else None,
            "delta": delta.model_dump(mode="json") if delta is not None else None,
        }
    )


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
    schedule_policy_id: Annotated[str | None, typer.Option("--schedule-policy-id")] = None,
    schedule_enabled: Annotated[
        bool | None, typer.Option("--schedule-enabled/--schedule-disabled")
    ] = None,
    preferred_run_time: Annotated[str | None, typer.Option("--preferred-run-time")] = None,
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
            schedule_policy_id=schedule_policy_id,
            schedule_enabled=schedule_enabled,
            preferred_run_time=preferred_run_time,
            panel_policy=panel_policy,
            memo_label_profile=memo_label_profile,
            notes=notes,
        )
    )
    _emit_json(entry.model_dump(mode="json"))


@app.command("list-cadence-policies")
def list_cadence_policies() -> None:
    _emit_json(CoverageService(_context()).list_cadence_policies())


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


@app.command("set-coverage-schedule")
def set_coverage_schedule(
    company_id: str,
    schedule_policy_id: Annotated[str | None, typer.Option("--schedule-policy-id")] = None,
    schedule_enabled: Annotated[
        bool | None, typer.Option("--schedule-enabled/--schedule-disabled")
    ] = None,
    preferred_run_time: Annotated[str | None, typer.Option("--preferred-run-time")] = None,
) -> None:
    entry = CoverageService(_context()).set_schedule(
        company_id,
        **({"schedule_policy_id": schedule_policy_id} if schedule_policy_id is not None else {}),
        **({"schedule_enabled": schedule_enabled} if schedule_enabled is not None else {}),
        **({"preferred_run_time": preferred_run_time} if preferred_run_time is not None else {}),
    )
    _emit_json(entry.model_dump(mode="json"))


@app.command("analyze-company")
def analyze_company(company_id: str) -> None:
    result = AnalysisService(_context()).analyze_company(company_id)
    _emit_json(_attach_recommendation_scope(result))


@app.command("run-panel")
def run_panel(company_id: str, panel_id: str) -> None:
    result = AnalysisService(_context()).run_panel(company_id, panel_id)
    _emit_json(result)


@app.command("refresh-company")
def refresh_company(company_id: str) -> None:
    result = AnalysisService(_context()).refresh_company(company_id)
    _emit_json(_attach_recommendation_scope(result))


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
    _emit_json(_attach_recommendation_scope(result))


@app.command("run-due-coverage")
def run_due_coverage() -> None:
    result = AnalysisService(_context()).run_due_coverage()
    _emit_json([_attach_recommendation_scope(item) for item in result])


@app.command("queue-summary")
def queue_summary() -> None:
    _emit_json(QueueService(_context()).get_queue_summary().model_dump(mode="json"))


@app.command("show-job")
def show_job(job_id: str) -> None:
    _emit_json(QueueService(_context()).get_job_detail(job_id).model_dump(mode="json"))


@app.command("enqueue-companies")
def enqueue_companies(
    company_ids: Annotated[list[str], typer.Argument()],
    requested_by: Annotated[str, typer.Option("--requested-by")] = "operator",
) -> None:
    jobs = QueueService(_context()).enqueue_companies(company_ids, requested_by=requested_by)
    _emit_json([job.model_dump(mode="json") for job in jobs])


@app.command("enqueue-watchlist")
def enqueue_watchlist(
    requested_by: Annotated[str, typer.Option("--requested-by")] = "operator",
) -> None:
    jobs = QueueService(_context()).enqueue_watchlist(requested_by=requested_by)
    _emit_json([job.model_dump(mode="json") for job in jobs])


@app.command("enqueue-portfolio")
def enqueue_portfolio(
    requested_by: Annotated[str, typer.Option("--requested-by")] = "operator",
) -> None:
    jobs = QueueService(_context()).enqueue_portfolio(requested_by=requested_by)
    _emit_json([job.model_dump(mode="json") for job in jobs])


@app.command("enqueue-due-coverage")
def enqueue_due_coverage(
    requested_by: Annotated[str, typer.Option("--requested-by")] = "scheduler",
) -> None:
    jobs = QueueService(_context()).enqueue_due_coverage(requested_by=requested_by)
    _emit_json([job.model_dump(mode="json") for job in jobs])


@app.command("retry-job")
def retry_job(job_id: str) -> None:
    _emit_json(QueueService(_context()).retry_job(job_id).model_dump(mode="json"))


@app.command("cancel-job")
def cancel_job(
    job_id: str,
    reason: Annotated[str | None, typer.Option("--reason")] = None,
) -> None:
    _emit_json(QueueService(_context()).cancel_job(job_id, reason=reason).model_dump(mode="json"))


@app.command("force-run-job")
def force_run_job(job_id: str) -> None:
    _emit_json(QueueService(_context()).force_run_job(job_id).model_dump(mode="json"))


@app.command("list-review-queue")
def list_review_queue() -> None:
    items = QueueService(_context()).list_review_queue()
    _emit_json([item.model_dump(mode="json") for item in items])


@app.command("run-worker")
def run_worker(
    limit: Annotated[int, typer.Option("--limit", min=1)] = 10,
    worker_id: Annotated[str, typer.Option("--worker-id")] = "worker",
    max_concurrency: Annotated[int, typer.Option("--max-concurrency", min=1)] = 1,
) -> None:
    results = WorkerService(_context()).run_available_jobs(
        limit=limit,
        worker_id=worker_id,
        max_concurrency=max_concurrency,
    )
    _emit_json(results)


@app.command("list-notifications")
def list_notifications() -> None:
    events = NotificationService(_context()).list_events()
    _emit_json([event.model_dump(mode="json") for event in events])


@app.command("claim-notifications")
def claim_notifications(
    consumer_id: Annotated[str, typer.Option("--consumer-id")] = "n8n",
    limit: Annotated[int, typer.Option("--limit", min=1)] = 10,
) -> None:
    events = NotificationService(_context()).claim_pending_events(
        limit=limit,
        consumer_id=consumer_id,
    )
    _emit_json([event.model_dump(mode="json") for event in events])


@app.command("dispatch-notification")
def dispatch_notification(event_id: str) -> None:
    _emit_json(NotificationService(_context()).mark_dispatched(event_id).model_dump(mode="json"))


@app.command("acknowledge-notification")
def acknowledge_notification(event_id: str) -> None:
    _emit_json(NotificationService(_context()).acknowledge(event_id).model_dump(mode="json"))


@app.command("generate-memo")
def generate_memo(company_id: str) -> None:
    memo = AnalysisService(_context()).generate_memo(company_id)
    typer.echo(render_memo_markdown(memo))


@app.command("show-delta")
def show_delta(company_id: str) -> None:
    delta = AnalysisService(_context()).show_delta(company_id)
    typer.echo(render_delta_json(delta))


@app.command("show-monitoring-history")
def show_monitoring_history(
    company_id: str,
    limit: Annotated[int | None, typer.Option("--limit", min=1)] = None,
) -> None:
    history = PortfolioReadService(_context()).get_company_monitoring_history(
        company_id,
        limit=limit,
    )
    _emit_json(history.model_dump(mode="json"))


@app.command("show-portfolio-summary")
def show_portfolio_summary(
    segment: Annotated[str, typer.Option("--segment")] = "all",
) -> None:
    summary = PortfolioReadService(_context()).get_portfolio_monitoring_summary(
        coverage_statuses=_resolve_summary_segment_option(segment)
    )
    _emit_json(summary.model_dump(mode="json"))


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
