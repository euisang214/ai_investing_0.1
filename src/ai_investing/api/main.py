from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from ai_investing.application.context import AppContext
from ai_investing.application.services import AgentConfigService, AnalysisService, CoverageService, IngestionService
from ai_investing.domain.enums import Cadence, CompanyType, CoverageStatus
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


context = AppContext.load()
app = FastAPI(title="AI Investing")


@app.on_event("startup")
def on_startup() -> None:
    context.database.initialize()


@app.post("/coverage")
def create_coverage(payload: CoverageCreateRequest) -> dict:
    service = CoverageService(context)
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
    return entry.model_dump(mode="json")


@app.get("/coverage")
def list_coverage() -> list[dict]:
    return [entry.model_dump(mode="json") for entry in CoverageService(context).list_coverage()]


@app.post("/coverage/run-due")
def run_due() -> list[dict]:
    return AnalysisService(context).run_due_coverage()


@app.post("/companies/{company_id}/ingest-public")
def ingest_public(company_id: str, payload: IngestRequest) -> dict:
    del company_id
    profile, evidence_ids = IngestionService(context).ingest_public_data(Path(payload.input_dir))
    return {"profile": profile.model_dump(mode="json"), "evidence_ids": evidence_ids}


@app.post("/companies/{company_id}/ingest-private")
def ingest_private(company_id: str, payload: IngestRequest) -> dict:
    del company_id
    profile, evidence_ids = IngestionService(context).ingest_private_data(Path(payload.input_dir))
    return {"profile": profile.model_dump(mode="json"), "evidence_ids": evidence_ids}


@app.post("/companies/{company_id}/analyze")
def analyze_company(company_id: str) -> dict:
    try:
        return AnalysisService(context).analyze_company(company_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/companies/{company_id}/refresh")
def refresh_company(company_id: str) -> dict:
    try:
        return AnalysisService(context).refresh_company(company_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/companies/{company_id}/panels/{panel_id}/run")
def run_panel(company_id: str, panel_id: str) -> dict:
    try:
        return AnalysisService(context).run_panel(company_id, panel_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/companies/{company_id}/memo")
def get_memo(company_id: str) -> dict:
    try:
        return AnalysisService(context).generate_memo(company_id).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/companies/{company_id}/delta")
def get_delta(company_id: str) -> dict:
    try:
        return AnalysisService(context).show_delta(company_id).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/agents")
def list_agents() -> list[dict]:
    return [agent.model_dump(mode="json") for agent in AgentConfigService(context).list_agents()]


@app.post("/agents/{agent_id}/enable")
def enable_agent(agent_id: str) -> dict:
    return AgentConfigService(context).enable_agent(agent_id).model_dump(mode="json")


@app.post("/agents/{agent_id}/disable")
def disable_agent(agent_id: str) -> dict:
    return AgentConfigService(context).disable_agent(agent_id).model_dump(mode="json")

