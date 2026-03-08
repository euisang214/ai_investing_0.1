from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml

from ai_investing.application.context import AppContext
from ai_investing.config.models import AgentConfig, PanelConfig
from ai_investing.domain.enums import (
    AlertLevel,
    Cadence,
    ChangeClassification,
    CompanyType,
    GateDecision,
    MemoSectionStatus,
    RecordStatus,
    RunKind,
    RunStatus,
    VerdictRecommendation,
)
from ai_investing.domain.models import (
    ClaimCard,
    CompanyProfile,
    CoverageEntry,
    GatekeeperVerdict,
    ICMemo,
    MemoSection,
    MemoSectionUpdate,
    MonitoringDelta,
    PanelVerdict,
    RunRecord,
    StructuredGenerationRequest,
    new_id,
    utc_now,
)
from ai_investing.ingestion.file_connectors import FileBundleConnector
from ai_investing.persistence.repositories import Repository


@dataclass
class AgentConfigService:
    context: AppContext

    def list_agents(self) -> list[AgentConfig]:
        return sorted(self.context.registries.agents.agents, key=lambda agent: agent.id)

    def enable_agent(self, agent_id: str) -> AgentConfig:
        return self._update_agent(agent_id, {"enabled": True})

    def disable_agent(self, agent_id: str) -> AgentConfig:
        return self._update_agent(agent_id, {"enabled": False})

    def reparent_agent(self, agent_id: str, new_parent_id: str | None) -> AgentConfig:
        return self._update_agent(agent_id, {"parent_id": new_parent_id})

    def _update_agent(self, agent_id: str, updates: dict[str, Any]) -> AgentConfig:
        with self.context.agents_config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        agents = data.get("agents", [])
        updated: dict[str, Any] | None = None
        for agent in agents:
            if agent["id"] == agent_id:
                agent.update(updates)
                updated = agent
                break
        if updated is None:
            raise KeyError(agent_id)
        with self.context.agents_config_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, sort_keys=False)
        self.context.reload_registries()
        return AgentConfig.model_validate(updated)


@dataclass
class CoverageService:
    context: AppContext

    def add_coverage(self, entry: CoverageEntry) -> CoverageEntry:
        if entry.next_run_at is None and entry.cadence == Cadence.WEEKLY:
            entry.next_run_at = utc_now()
        with self.context.database.session() as session:
            repository = Repository(session)
            return repository.upsert_coverage(entry)

    def list_coverage(self) -> list[CoverageEntry]:
        with self.context.database.session() as session:
            repository = Repository(session)
            return repository.list_coverage()

    def disable_coverage(self, company_id: str) -> CoverageEntry:
        with self.context.database.session() as session:
            repository = Repository(session)
            entry = repository.get_coverage(company_id)
            if entry is None:
                raise KeyError(company_id)
            entry.enabled = False
            return repository.upsert_coverage(entry)

    def remove_coverage(self, company_id: str) -> None:
        with self.context.database.session() as session:
            repository = Repository(session)
            repository.remove_coverage(company_id)


@dataclass
class IngestionService:
    context: AppContext

    def ingest_public_data(self, input_dir: Path) -> tuple[CompanyProfile, list[str]]:
        return self._ingest(company_type=CompanyType.PUBLIC, input_dir=input_dir)

    def ingest_private_data(self, input_dir: Path) -> tuple[CompanyProfile, list[str]]:
        return self._ingest(company_type=CompanyType.PRIVATE, input_dir=input_dir)

    def _ingest(self, *, company_type: CompanyType, input_dir: Path) -> tuple[CompanyProfile, list[str]]:
        connector_id = "public_file_connector" if company_type == CompanyType.PUBLIC else "private_file_connector"
        connector_config = next(
            connector
            for connector in self.context.registries.source_connectors.connectors
            if connector.id == connector_id
        )
        connector = FileBundleConnector(raw_landing_zone=Path(connector_config.raw_landing_zone))
        profile, records = connector.ingest(input_dir)
        with self.context.database.session() as session:
            repository = Repository(session)
            repository.save_company_profile(profile)
            repository.save_evidence_records(records)
        return profile, [record.evidence_id for record in records]


@dataclass
class RefreshRuntime:
    context: AppContext
    repository: Repository
    run: RunRecord
    coverage: CoverageEntry
    company_profile: CompanyProfile
    prior_memo: ICMemo | None
    prior_active_claims: list[ClaimCard]
    current_sections: dict[str, MemoSection]
    current_claims: list[ClaimCard]
    current_verdicts: dict[str, PanelVerdict]
    current_delta: MonitoringDelta | None = None

    @classmethod
    def create(
        cls,
        *,
        context: AppContext,
        repository: Repository,
        run: RunRecord,
        coverage: CoverageEntry,
        company_profile: CompanyProfile,
    ) -> "RefreshRuntime":
        prior_memo = repository.get_current_memo(company_profile.company_id)
        prior_active_claims = repository.list_claim_cards(company_profile.company_id, active_only=True)
        current_sections = (
            prior_memo.section_map() if prior_memo is not None else {}
        )
        return cls(
            context=context,
            repository=repository,
            run=run,
            coverage=coverage,
            company_profile=company_profile,
            prior_memo=prior_memo,
            prior_active_claims=prior_active_claims,
            current_sections=current_sections,
            current_claims=[],
            current_verdicts={},
        )

    def execute_panel(self, panel_id: str) -> dict[str, Any]:
        panel = self.context.get_panel(panel_id)
        evidence = self.repository.list_evidence(self.company_profile.company_id, panel_id=panel_id)
        specialist_claims = self._run_specialists(panel=panel, evidence=evidence)
        verdict = self._run_judge(panel=panel, claims=specialist_claims)
        self.current_claims.extend(specialist_claims)
        return {
            "claims": [claim.model_dump(mode="json") for claim in specialist_claims],
            "verdict": verdict.model_dump(mode="json"),
        }

    def update_memo_for_panel(self, panel_id: str) -> dict[str, Any]:
        verdict = self.current_verdicts[panel_id]
        panel_claims = [claim for claim in self.current_claims if claim.panel_id == panel_id]
        updates: list[MemoSectionUpdate] = []
        for section_id in verdict.affected_section_ids:
            label = self.context.memo_section_labels(self.coverage.memo_label_profile)[section_id]
            prior_text = self.current_sections.get(section_id).content if section_id in self.current_sections else ""
            provider = self.context.get_provider("balanced")
            prompt = self.context.prompt_loader.load("prompts/memo_updates/section_update.md")
            update = provider.generate_structured(
                StructuredGenerationRequest(
                    task_type="memo_section_update",
                    prompt=prompt,
                    input_data={
                        "company_id": self.company_profile.company_id,
                        "run_id": self.run.run_id,
                        "section_id": section_id,
                        "prior_text": prior_text,
                        "verdicts": [verdict.model_dump(mode="json")],
                        "claims": [claim.model_dump(mode="json") for claim in panel_claims],
                    },
                ),
                MemoSectionUpdate,
            )
            section = MemoSection(
                section_id=section_id,
                label=label,
                content=update.updated_text,
                status=MemoSectionStatus.REFRESHED,
                supporting_claim_ids=update.supporting_claim_ids,
                supporting_verdict_ids=[verdict.verdict_id],
                updated_by_run_id=self.run.run_id,
            )
            self.current_sections[section_id] = section
            self.repository.save_memo_section_update(update)
            updates.append(update)

        partial_memo = self._build_memo(is_partial=True)
        self.repository.save_memo(partial_memo)
        return {
            "updates": [update.model_dump(mode="json") for update in updates],
            "memo": partial_memo.model_dump(mode="json"),
        }

    def compute_monitoring_delta(self) -> MonitoringDelta:
        prior_claim_map = {
            (claim.factor_id, claim.agent_id): claim for claim in self.prior_active_claims
        }
        changed_claim_ids: list[str] = []
        drift_flags: set[str] = set()
        for claim in self.current_claims:
            prior_claim = prior_claim_map.get((claim.factor_id, claim.agent_id))
            if prior_claim is None:
                changed_claim_ids.append(claim.claim_id)
                continue
            if (
                prior_claim.claim != claim.claim
                or prior_claim.bull_case != claim.bull_case
                or abs(prior_claim.confidence - claim.confidence) >= 0.1
            ):
                changed_claim_ids.append(claim.claim_id)
                if claim.factor_id == "customer_concentration":
                    drift_flags.add("concentration_increase")
                if claim.factor_id == "balance_sheet_survivability":
                    drift_flags.add("survivability_deterioration")
                if claim.factor_id == "revenue_recurrence_contract_strength":
                    drift_flags.add("weakening_recurrence")
                if claim.factor_id == "governance_investability":
                    drift_flags.add("governance_risk_increase")

        if self.prior_memo is None:
            summary = "Initial coverage run. No prior memo exists."
            alert_level = AlertLevel.LOW
        else:
            summary = ""
            alert_level = AlertLevel.LOW
        delta = MonitoringDelta(
            company_id=self.company_profile.company_id,
            prior_run_id=self.prior_memo.run_id if self.prior_memo is not None else None,
            current_run_id=self.run.run_id,
            changed_claim_ids=changed_claim_ids,
            changed_sections=[],
            change_summary=summary,
            thesis_drift_flags=sorted(drift_flags),
            alert_level=alert_level,
        )
        self._update_delta_section(delta)
        changed_sections = [
            section_id
            for section_id, section in self.current_sections.items()
            if self.prior_memo is None
            or self.prior_memo.section_map().get(
                section_id,
                MemoSection(section_id=section_id, label=section.label, content=""),
            ).content
            != section.content
        ]
        delta.changed_sections = changed_sections
        if self.prior_memo is not None:
            delta.change_summary = (
                f"{self.company_profile.company_name} changed in {len(changed_sections)} memo sections "
                f"with {len(changed_claim_ids)} materially updated claim cards."
            )
            high_sections = set(
                self.context.registries.monitoring.monitoring.delta_thresholds.get(
                    "high_alert_changed_sections", []
                )
            )
            if high_sections.intersection(changed_sections):
                delta.alert_level = AlertLevel.HIGH
            elif changed_claim_ids:
                delta.alert_level = AlertLevel.MEDIUM
            else:
                delta.alert_level = AlertLevel.LOW
        self.current_delta = delta
        self.repository.save_monitoring_delta(delta)
        return delta

    def reconcile_ic_memo(self) -> ICMemo:
        memo = self._build_memo(is_partial=False)
        self.repository.save_memo(memo)
        return memo

    def _run_specialists(self, *, panel: PanelConfig, evidence: list[Any]) -> list[ClaimCard]:
        claims: list[ClaimCard] = []
        specialist_agents = [
            agent
            for agent in self.context.active_agents_for_panel(panel.id)
            if agent.role_type in {"specialist", "skeptic", "durability"}
        ]
        for factor_id in panel.factor_ids:
            factor_name = self.context.get_factor_name(factor_id)
            for agent in specialist_agents:
                tool_evidence = self.context.tool_registry.execute(
                    repository=self.repository,
                    agent=agent,
                    company_id=self.company_profile.company_id,
                    run_id=self.run.run_id,
                    tool_id="evidence_search",
                    payload={"panel_id": panel.id, "factor_id": factor_id},
                )["records"]
                prior_claims = self.context.tool_registry.execute(
                    repository=self.repository,
                    agent=agent,
                    company_id=self.company_profile.company_id,
                    run_id=self.run.run_id,
                    tool_id="claim_search",
                    payload={"panel_id": panel.id, "factor_id": factor_id, "active_only": True},
                )["claims"]
                prompt = self.context.prompt_loader.load(agent.prompt_path)
                provider = self.context.get_provider(agent.model_profile)
                prior_claim_text = prior_claims[0]["claim"] if prior_claims else ""
                claim = provider.generate_structured(
                    StructuredGenerationRequest(
                        task_type="claim_card",
                        prompt=prompt,
                        input_data={
                            "company_id": self.company_profile.company_id,
                            "company_name": self.company_profile.company_name,
                            "company_type": self.company_profile.company_type.value,
                            "run_id": self.run.run_id,
                            "panel_id": panel.id,
                            "factor_id": factor_id,
                            "factor_name": factor_name,
                            "agent_id": agent.id,
                            "role_type": agent.role_type,
                            "evidence": tool_evidence,
                            "prior_claim": prior_claim_text,
                            "section_ids": panel.memo_section_ids,
                            "namespace": f"company/{self.company_profile.company_id}/claims/{factor_id}",
                        },
                    ),
                    ClaimCard,
                )
                claims.append(claim)
        self.repository.save_claim_cards(claims)
        return claims

    def _run_judge(self, *, panel: PanelConfig, claims: list[ClaimCard]) -> PanelVerdict:
        judge = next(
            agent
            for agent in self.context.active_agents_for_panel(panel.id)
            if agent.role_type == "judge"
        )
        provider = self.context.get_provider(judge.model_profile)
        prompt = self.context.prompt_loader.load(judge.prompt_path)
        response_model = GatekeeperVerdict if panel.id == "gatekeepers" else PanelVerdict
        verdict = provider.generate_structured(
            StructuredGenerationRequest(
                task_type="panel_verdict",
                prompt=prompt,
                input_data={
                    "company_id": self.company_profile.company_id,
                    "company_name": self.company_profile.company_name,
                    "company_type": self.company_profile.company_type.value,
                    "run_id": self.run.run_id,
                    "panel_id": panel.id,
                    "panel_name": panel.name,
                    "claims": [claim.model_dump(mode="json") for claim in claims],
                    "affected_section_ids": panel.memo_section_ids,
                    "namespace": f"company/{self.company_profile.company_id}/verdicts/{panel.id}",
                },
            ),
            response_model,
        )
        self.repository.save_panel_verdict(verdict)
        return verdict

    def finalize_panel_verdict(self, *, panel_id: str, verdict: PanelVerdict) -> PanelVerdict:
        panel = self.context.get_panel(panel_id)
        lead_agents = [
            agent
            for agent in self.context.active_agents_for_panel(panel.id)
            if agent.role_type == "lead"
        ]
        if not lead_agents:
            self.current_verdicts[panel_id] = verdict
            return verdict
        lead = lead_agents[0]
        summary_prefix = "Gatekeeper lead:" if panel.id == "gatekeepers" else "Panel lead:"
        updated = verdict.model_copy(
            update={
                "verdict_id": new_id("vrd"),
                "summary": f"{summary_prefix} {verdict.summary}",
                "supersedes_verdict_id": verdict.verdict_id,
            }
        )
        self.repository.save_panel_verdict(updated)
        self.current_verdicts[panel_id] = updated
        return updated

    def _build_memo(self, *, is_partial: bool) -> ICMemo:
        labels = self.context.memo_section_labels(self.coverage.memo_label_profile)
        ordered_sections: list[MemoSection] = []
        for section_id, label in labels.items():
            section = self.current_sections.get(section_id)
            if section is None:
                status = MemoSectionStatus.DRAFT if is_partial else MemoSectionStatus.PENDING
                content = "Pending update."
                if section_id == "what_changed_since_last_run":
                    content = (
                        "Initial coverage run."
                        if self.prior_memo is None
                        else "Waiting for monitoring diff."
                    )
                section = MemoSection(
                    section_id=section_id,
                    label=label,
                    content=content,
                    status=status,
                )
            ordered_sections.append(section)
        provider = self.context.get_provider("quality")
        prompt = self.context.prompt_loader.load("prompts/ic/synthesizer.md")
        return provider.generate_structured(
            StructuredGenerationRequest(
                task_type="ic_memo",
                prompt=prompt,
                input_data={
                    "company_id": self.company_profile.company_id,
                    "run_id": self.run.run_id,
                    "is_initial_coverage": self.prior_memo is None,
                    "sections": [section.model_dump(mode="json") for section in ordered_sections],
                    "section_labels": list(labels.items()),
                    "namespace": f"company/{self.company_profile.company_id}/memos/current",
                },
            ),
            ICMemo,
        )

    def _update_delta_section(self, delta: MonitoringDelta) -> None:
        label = self.context.memo_section_labels(self.coverage.memo_label_profile)[
            "what_changed_since_last_run"
        ]
        if self.prior_memo is None:
            content = "Initial coverage run. No prior memo exists."
        else:
            changed = ", ".join(delta.changed_sections) if delta.changed_sections else "no memo sections"
            content = f"{delta.change_summary} Changed sections: {changed}."
        self.current_sections["what_changed_since_last_run"] = MemoSection(
            section_id="what_changed_since_last_run",
            label=label,
            content=content,
            status=MemoSectionStatus.REFRESHED,
            updated_by_run_id=self.run.run_id,
        )


@dataclass
class AnalysisService:
    context: AppContext

    def initialize_database(self) -> None:
        self.context.database.initialize()

    def analyze_company(self, company_id: str, panel_ids: list[str] | None = None) -> dict[str, Any]:
        return self._run_company(company_id=company_id, panel_ids=panel_ids, run_kind=RunKind.ANALYZE)

    def refresh_company(self, company_id: str) -> dict[str, Any]:
        return self._run_company(company_id=company_id, panel_ids=None, run_kind=RunKind.REFRESH)

    def run_panel(self, company_id: str, panel_id: str) -> dict[str, Any]:
        return self._run_company(
            company_id=company_id,
            panel_ids=[panel_id],
            run_kind=RunKind.PANEL,
        )

    def run_due_coverage(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        with self.context.database.session() as session:
            repository = Repository(session)
            due_entries = repository.list_coverage(enabled_only=True, due_only=True, now=utc_now())
        for entry in due_entries:
            results.append(self.refresh_company(entry.company_id))
        return results

    def generate_memo(self, company_id: str) -> ICMemo:
        with self.context.database.session() as session:
            repository = Repository(session)
            memo = repository.get_current_memo(company_id)
            if memo is None:
                raise KeyError(company_id)
            return memo

    def show_delta(self, company_id: str) -> MonitoringDelta:
        with self.context.database.session() as session:
            repository = Repository(session)
            delta = repository.get_latest_monitoring_delta(company_id)
            if delta is None:
                raise KeyError(company_id)
            return delta

    def _run_company(
        self, *, company_id: str, panel_ids: list[str] | None, run_kind: RunKind
    ) -> dict[str, Any]:
        with self.context.database.session() as session:
            repository = Repository(session)
            coverage = repository.get_coverage(company_id)
            if coverage is None:
                raise KeyError(f"No coverage entry for {company_id}")
            company_profile = repository.get_company_profile(company_id)
            if company_profile is None:
                raise KeyError(f"No company profile for {company_id}")
            run = RunRecord(company_id=company_id, run_kind=run_kind, status=RunStatus.RUNNING)
            repository.save_run(run)
            runtime = RefreshRuntime.create(
                context=self.context,
                repository=repository,
                run=run,
                coverage=coverage,
                company_profile=company_profile,
            )
            selected_panels = panel_ids or self._panel_ids_for_coverage(coverage)
            from ai_investing.graphs.company_refresh import build_company_refresh_graph

            graph = build_company_refresh_graph(runtime=runtime, panel_ids=selected_panels)
            graph_result = graph.invoke(
                {
                    "company_id": company_id,
                    "run_id": run.run_id,
                    "panel_ids": selected_panels,
                }
            )
            run.status = RunStatus.COMPLETE
            run.completed_at = utc_now()
            repository.save_run(run)
            coverage.last_run_at = run.completed_at
            if coverage.cadence == Cadence.WEEKLY and run.completed_at is not None:
                coverage.next_run_at = run.completed_at + timedelta(days=7)
            repository.upsert_coverage(coverage)
            return {
                "run": run.model_dump(mode="json"),
                "panels": graph_result.get("panel_results", {}),
                "memo": graph_result["memo"],
                "delta": graph_result["delta"],
            }

    def _panel_ids_for_coverage(self, coverage: CoverageEntry) -> list[str]:
        policy = self.context.registries.run_policies.run_policies[coverage.panel_policy]
        return list(policy.default_panel_ids)


def render_memo_markdown(memo: ICMemo) -> str:
    lines = [f"# IC Memo: {memo.company_id}", ""]
    for section in memo.sections:
        lines.append(f"## {section.label}")
        lines.append(section.content)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_delta_json(delta: MonitoringDelta) -> str:
    return json.dumps(delta.model_dump(mode="json"), indent=2)
