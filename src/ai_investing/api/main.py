from __future__ import annotations

from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from ai_investing.application.context import AppContext
from ai_investing.application.notifications import NotificationService
from ai_investing.application.portfolio import PortfolioReadService, resolve_summary_segments
from ai_investing.application.queue import QueueService
from ai_investing.application.services import (
    AgentConfigService,
    AnalysisService,
    CoverageService,
    IngestionService,
)
from ai_investing.application.worker import WorkerService
from ai_investing.domain.enums import Cadence, CompanyType, CoverageStatus, RunContinueAction
from ai_investing.domain.models import (
    ClaimCard,
    CoverageEntry,
    GatekeeperVerdict,
    ICMemo,
    MonitoringDelta,
    PanelVerdict,
    RunRecord,
)
from ai_investing.domain.read_models import CompanyMonitoringHistory, PortfolioMonitoringSummary
from ai_investing.persistence.repositories import Repository


class CoverageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str
    company_name: str
    company_type: CompanyType
    coverage_status: CoverageStatus
    cadence: Cadence = Cadence.WEEKLY
    schedule_policy_id: str | None = None
    schedule_enabled: bool | None = None
    preferred_run_time: str | None = None
    panel_policy: str = "weekly_default"
    memo_label_profile: str = "default"
    notes: str | None = None


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_dir: str


class NextRunAtRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_run_at: str | None = None


class CoverageScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_policy_id: str | None = None
    schedule_enabled: bool | None = None
    preferred_run_time: str | None = None


class ReparentAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: str | None = None


class EnqueueCompaniesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_ids: list[str] = Field(default_factory=list)
    requested_by: str = "operator"


class RequestedByRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_by: str = "operator"


class JobCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class WorkerRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = 10
    worker_id: str = "worker"
    max_concurrency: int = 1


class NotificationClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = 10
    consumer_id: str = "n8n"


class ContinueRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: RunContinueAction = RunContinueAction.CONTINUE


class PanelResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[ClaimCard] = Field(default_factory=list)
    verdict: GatekeeperVerdict | PanelVerdict


class RunResultResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: RunRecord
    panels: dict[str, PanelResultResponse] = Field(default_factory=dict)
    memo: ICMemo | None = None
    delta: MonitoringDelta | None = None


class RunResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: RunResultResponseData


class RunResultListEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[RunResultResponseData] = Field(default_factory=list)


class CompanyMonitoringHistoryEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: CompanyMonitoringHistory


class PortfolioMonitoringSummaryEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: PortfolioMonitoringSummary


def create_app(context: AppContext | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime_context = context if context is not None else AppContext.load()
        runtime_context.database.initialize()
        app.state.context = runtime_context
        yield

    app = FastAPI(title="AI Investing", lifespan=lifespan)

    @app.exception_handler(KeyError)
    async def handle_not_found(_: Request, exc: KeyError) -> JSONResponse:
        return _error_response(
            code="not_found",
            message=_exception_message(exc),
            status_code=status.HTTP_404_NOT_FOUND,
        )

    @app.exception_handler(ValueError)
    async def handle_invalid_request(_: Request, exc: ValueError) -> JSONResponse:
        return _error_response(
            code="invalid_request",
            message=_exception_message(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(FileNotFoundError)
    async def handle_missing_input(_: Request, exc: FileNotFoundError) -> JSONResponse:
        return _error_response(
            code="input_not_found",
            message=str(exc),
            status_code=status.HTTP_404_NOT_FOUND,
        )

    @app.post("/coverage", status_code=status.HTTP_201_CREATED)
    def create_coverage(payload: CoverageCreateRequest, request: Request) -> JSONResponse:
        service = CoverageService(_context(request))
        entry = service.add_coverage(
            CoverageEntry(
                company_id=payload.company_id,
                company_name=payload.company_name,
                company_type=payload.company_type,
                coverage_status=payload.coverage_status,
                cadence=payload.cadence,
                schedule_policy_id=payload.schedule_policy_id,
                schedule_enabled=payload.schedule_enabled,
                preferred_run_time=payload.preferred_run_time,
                panel_policy=payload.panel_policy,
                memo_label_profile=payload.memo_label_profile,
                notes=payload.notes,
            )
        )
        return _success_response(entry.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)

    @app.get("/cadence-policies")
    def list_cadence_policies(request: Request) -> JSONResponse:
        payload = CoverageService(_context(request)).list_cadence_policies()
        return _success_response(payload)

    @app.get("/coverage")
    def list_coverage(request: Request) -> JSONResponse:
        entries = CoverageService(_context(request)).list_coverage()
        payload = [entry.model_dump(mode="json") for entry in entries]
        return _success_response(payload)

    @app.post("/coverage/{company_id}/disable")
    def disable_coverage(company_id: str, request: Request) -> JSONResponse:
        entry = CoverageService(_context(request)).disable_coverage(company_id)
        return _success_response(entry.model_dump(mode="json"))

    @app.delete("/coverage/{company_id}")
    def remove_coverage(company_id: str, request: Request) -> JSONResponse:
        CoverageService(_context(request)).remove_coverage(company_id)
        return _success_response({"company_id": company_id, "removed": True})

    @app.post("/coverage/{company_id}/next-run-at")
    def set_next_run_at(
        company_id: str,
        payload: NextRunAtRequest,
        request: Request,
    ) -> JSONResponse:
        next_run_at = _parse_datetime(payload.next_run_at) if payload.next_run_at else None
        entry = CoverageService(_context(request)).set_next_run_at(company_id, next_run_at)
        return _success_response(entry.model_dump(mode="json"))

    @app.post("/coverage/{company_id}/schedule")
    def set_coverage_schedule(
        company_id: str,
        payload: CoverageScheduleRequest,
        request: Request,
    ) -> JSONResponse:
        fields_set = payload.model_fields_set
        service = CoverageService(_context(request))
        entry = service.set_schedule(
            company_id,
            **(
                {"schedule_policy_id": payload.schedule_policy_id}
                if "schedule_policy_id" in fields_set
                else {}
            ),
            **(
                {"schedule_enabled": payload.schedule_enabled}
                if "schedule_enabled" in fields_set
                else {}
            ),
            **(
                {"preferred_run_time": payload.preferred_run_time}
                if "preferred_run_time" in fields_set
                else {}
            ),
        )
        return _success_response(entry.model_dump(mode="json"))

    @app.post("/coverage/run-due", response_model=RunResultListEnvelope)
    def run_due(request: Request) -> RunResultListEnvelope:
        return _run_result_list_response(AnalysisService(_context(request)).run_due_coverage())

    @app.get("/queue")
    def get_queue_summary(request: Request) -> JSONResponse:
        summary = QueueService(_context(request)).get_queue_summary()
        return _success_response(summary.model_dump(mode="json"))

    @app.get("/queue/{job_id}")
    def get_queue_job(job_id: str, request: Request) -> JSONResponse:
        detail = QueueService(_context(request)).get_job_detail(job_id)
        return _success_response(detail.model_dump(mode="json"))

    @app.post("/queue/enqueue-selected")
    def enqueue_selected(
        payload: EnqueueCompaniesRequest,
        request: Request,
    ) -> JSONResponse:
        jobs = QueueService(_context(request)).enqueue_companies(
            payload.company_ids,
            requested_by=payload.requested_by,
        )
        return _success_response([job.model_dump(mode="json") for job in jobs])

    @app.post("/queue/enqueue-watchlist")
    def enqueue_watchlist(payload: RequestedByRequest, request: Request) -> JSONResponse:
        jobs = QueueService(_context(request)).enqueue_watchlist(requested_by=payload.requested_by)
        return _success_response([job.model_dump(mode="json") for job in jobs])

    @app.post("/queue/enqueue-portfolio")
    def enqueue_portfolio(payload: RequestedByRequest, request: Request) -> JSONResponse:
        jobs = QueueService(_context(request)).enqueue_portfolio(requested_by=payload.requested_by)
        return _success_response([job.model_dump(mode="json") for job in jobs])

    @app.post("/queue/enqueue-due")
    def enqueue_due(payload: RequestedByRequest, request: Request) -> JSONResponse:
        jobs = QueueService(_context(request)).enqueue_due_coverage(
            requested_by=payload.requested_by
        )
        return _success_response([job.model_dump(mode="json") for job in jobs])

    @app.post("/queue/{job_id}/retry")
    def retry_job(job_id: str, request: Request) -> JSONResponse:
        job = QueueService(_context(request)).retry_job(job_id)
        return _success_response(job.model_dump(mode="json"))

    @app.post("/queue/{job_id}/cancel")
    def cancel_job(job_id: str, payload: JobCancelRequest, request: Request) -> JSONResponse:
        job = QueueService(_context(request)).cancel_job(job_id, reason=payload.reason)
        return _success_response(job.model_dump(mode="json"))

    @app.post("/queue/{job_id}/force-run")
    def force_run_job(job_id: str, request: Request) -> JSONResponse:
        job = QueueService(_context(request)).force_run_job(job_id)
        return _success_response(job.model_dump(mode="json"))

    @app.get("/review-queue")
    def get_review_queue(request: Request) -> JSONResponse:
        items = QueueService(_context(request)).list_review_queue()
        return _success_response([item.model_dump(mode="json") for item in items])

    @app.post("/workers/run")
    def run_worker(payload: WorkerRunRequest, request: Request) -> JSONResponse:
        results = WorkerService(_context(request)).run_available_jobs(
            limit=payload.limit,
            worker_id=payload.worker_id,
            max_concurrency=payload.max_concurrency,
        )
        return _success_response(results)

    @app.get("/notifications")
    def get_notifications(request: Request) -> JSONResponse:
        events = NotificationService(_context(request)).list_events()
        return _success_response([event.model_dump(mode="json") for event in events])

    @app.post("/notifications/claim")
    def claim_notifications(
        payload: NotificationClaimRequest,
        request: Request,
    ) -> JSONResponse:
        events = NotificationService(_context(request)).claim_pending_events(
            limit=payload.limit,
            consumer_id=payload.consumer_id,
        )
        return _success_response([event.model_dump(mode="json") for event in events])

    @app.post("/notifications/{event_id}/dispatch")
    def dispatch_notification(event_id: str, request: Request) -> JSONResponse:
        event = NotificationService(_context(request)).mark_dispatched(event_id)
        return _success_response(event.model_dump(mode="json"))

    @app.post("/notifications/{event_id}/acknowledge")
    def acknowledge_notification(event_id: str, request: Request) -> JSONResponse:
        event = NotificationService(_context(request)).acknowledge(event_id)
        return _success_response(event.model_dump(mode="json"))

    @app.post("/companies/{company_id}/ingest-public")
    def ingest_public(company_id: str, payload: IngestRequest, request: Request) -> JSONResponse:
        profile, evidence_ids = IngestionService(_context(request)).ingest_public_data(
            Path(payload.input_dir)
        )
        _validate_company_id(company_id, profile.company_id)
        return _success_response(
            {"profile": profile.model_dump(mode="json"), "evidence_ids": evidence_ids}
        )

    @app.post("/companies/{company_id}/ingest-private")
    def ingest_private(company_id: str, payload: IngestRequest, request: Request) -> JSONResponse:
        profile, evidence_ids = IngestionService(_context(request)).ingest_private_data(
            Path(payload.input_dir)
        )
        _validate_company_id(company_id, profile.company_id)
        return _success_response(
            {"profile": profile.model_dump(mode="json"), "evidence_ids": evidence_ids}
        )

    @app.post("/companies/{company_id}/analyze", response_model=RunResultEnvelope)
    def analyze_company(company_id: str, request: Request) -> RunResultEnvelope:
        result = AnalysisService(_context(request)).analyze_company(company_id)
        return _run_result_response(result)

    @app.post("/companies/{company_id}/refresh", response_model=RunResultEnvelope)
    def refresh_company(company_id: str, request: Request) -> RunResultEnvelope:
        result = AnalysisService(_context(request)).refresh_company(company_id)
        return _run_result_response(result)

    @app.get("/runs/{run_id}", response_model=RunResultEnvelope)
    def get_run(run_id: str, request: Request) -> RunResultEnvelope:
        return _run_result_response(_load_run_result(_context(request), run_id))

    @app.post("/runs/{run_id}/continue", response_model=RunResultEnvelope)
    def continue_run(
        run_id: str,
        payload: ContinueRunRequest,
        request: Request,
    ) -> RunResultEnvelope:
        result = AnalysisService(_context(request)).continue_run(run_id, action=payload.action)
        return _run_result_response(result)

    @app.post("/companies/{company_id}/panels/{panel_id}/run", response_model=RunResultEnvelope)
    def run_panel(company_id: str, panel_id: str, request: Request) -> RunResultEnvelope:
        result = AnalysisService(_context(request)).run_panel(company_id, panel_id)
        return _run_result_response(result)

    @app.get("/companies/{company_id}/memo")
    def get_memo(company_id: str, request: Request) -> JSONResponse:
        memo = AnalysisService(_context(request)).generate_memo(company_id)
        return _success_response(memo.model_dump(mode="json"))

    @app.get("/companies/{company_id}/delta")
    def get_delta(company_id: str, request: Request) -> JSONResponse:
        delta = AnalysisService(_context(request)).show_delta(company_id)
        return _success_response(delta.model_dump(mode="json"))

    @app.get(
        "/companies/{company_id}/monitoring-history",
        response_model=CompanyMonitoringHistoryEnvelope,
    )
    def get_monitoring_history(
        company_id: str,
        request: Request,
        limit: int | None = None,
    ) -> JSONResponse:
        history = PortfolioReadService(_context(request)).get_company_monitoring_history(
            company_id,
            limit=limit,
        )
        return _success_response(history.model_dump(mode="json"))

    @app.get(
        "/portfolio/monitoring-summary",
        response_model=PortfolioMonitoringSummaryEnvelope,
    )
    def get_portfolio_monitoring_summary(
        request: Request,
        segment: str = "all",
    ) -> JSONResponse:
        summary = PortfolioReadService(_context(request)).get_portfolio_monitoring_summary(
            coverage_statuses=resolve_summary_segments(segment)
        )
        return _success_response(summary.model_dump(mode="json"))

    @app.get("/agents")
    def list_agents(request: Request) -> JSONResponse:
        agents = AgentConfigService(_context(request)).list_agents()
        payload = [agent.model_dump(mode="json") for agent in agents]
        return _success_response(payload)

    @app.post("/agents/{agent_id}/enable")
    def enable_agent(agent_id: str, request: Request) -> JSONResponse:
        agent = AgentConfigService(_context(request)).enable_agent(agent_id)
        return _success_response(agent.model_dump(mode="json"))

    @app.post("/agents/{agent_id}/disable")
    def disable_agent(agent_id: str, request: Request) -> JSONResponse:
        agent = AgentConfigService(_context(request)).disable_agent(agent_id)
        return _success_response(agent.model_dump(mode="json"))

    @app.post("/agents/{agent_id}/reparent")
    def reparent_agent(
        agent_id: str,
        payload: ReparentAgentRequest,
        request: Request,
    ) -> JSONResponse:
        agent = AgentConfigService(_context(request)).reparent_agent(agent_id, payload.parent_id)
        return _success_response(agent.model_dump(mode="json"))

    return app


def _context(request: Request) -> AppContext:
    return request.app.state.context


def _exception_message(exc: Exception) -> str:
    if exc.args:
        return str(exc.args[0])
    return str(exc)


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            "Use an ISO-8601 timestamp, for example 2026-03-10T09:30:00+00:00."
        ) from exc


def _validate_company_id(requested_company_id: str, manifest_company_id: str) -> None:
    if requested_company_id != manifest_company_id:
        raise ValueError(
            "Path company_id "
            f"{requested_company_id} does not match manifest company_id "
            f"{manifest_company_id}."
        )


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


def _run_result_response(data: dict[str, Any]) -> RunResultEnvelope:
    return RunResultEnvelope(data=RunResultResponseData.model_validate(data))


def _run_result_list_response(data: list[dict[str, Any]]) -> RunResultListEnvelope:
    return RunResultListEnvelope(
        data=[RunResultResponseData.model_validate(item) for item in data]
    )


def _error_response(*, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _success_response(data: Any, *, status_code: int = status.HTTP_200_OK) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": jsonable_encoder(data)})


app = create_app()
