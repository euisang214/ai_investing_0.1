from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from ai_investing.application.context import AppContext
from ai_investing.application.services import (
    AgentConfigService,
    AnalysisService,
    CoverageService,
    IngestionService,
)
from ai_investing.domain.enums import Cadence, CompanyType, CoverageStatus, RunContinueAction
from ai_investing.domain.models import CoverageEntry


class CoverageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str
    company_name: str
    company_type: CompanyType
    coverage_status: CoverageStatus
    cadence: Cadence = Cadence.WEEKLY
    panel_policy: str = "weekly_default"
    memo_label_profile: str = "default"
    notes: str | None = None


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_dir: str


class NextRunAtRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_run_at: str | None = None


class ReparentAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: str | None = None


class ContinueRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: RunContinueAction = RunContinueAction.CONTINUE


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
                panel_policy=payload.panel_policy,
                memo_label_profile=payload.memo_label_profile,
                notes=payload.notes,
            )
        )
        return _success_response(entry.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)

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

    @app.post("/coverage/run-due")
    def run_due(request: Request) -> JSONResponse:
        return _success_response(AnalysisService(_context(request)).run_due_coverage())

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

    @app.post("/companies/{company_id}/analyze")
    def analyze_company(company_id: str, request: Request) -> JSONResponse:
        return _success_response(AnalysisService(_context(request)).analyze_company(company_id))

    @app.post("/companies/{company_id}/refresh")
    def refresh_company(company_id: str, request: Request) -> JSONResponse:
        return _success_response(AnalysisService(_context(request)).refresh_company(company_id))

    @app.post("/runs/{run_id}/continue")
    def continue_run(
        run_id: str,
        payload: ContinueRunRequest,
        request: Request,
    ) -> JSONResponse:
        result = AnalysisService(_context(request)).continue_run(run_id, action=payload.action)
        return _success_response(result)

    @app.post("/companies/{company_id}/panels/{panel_id}/run")
    def run_panel(company_id: str, panel_id: str, request: Request) -> JSONResponse:
        return _success_response(AnalysisService(_context(request)).run_panel(company_id, panel_id))

    @app.get("/companies/{company_id}/memo")
    def get_memo(company_id: str, request: Request) -> JSONResponse:
        memo = AnalysisService(_context(request)).generate_memo(company_id)
        return _success_response(memo.model_dump(mode="json"))

    @app.get("/companies/{company_id}/delta")
    def get_delta(company_id: str, request: Request) -> JSONResponse:
        delta = AnalysisService(_context(request)).show_delta(company_id)
        return _success_response(delta.model_dump(mode="json"))

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


def _error_response(*, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _success_response(data: Any, *, status_code: int = status.HTTP_200_OK) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": jsonable_encoder(data)})


app = create_app()
