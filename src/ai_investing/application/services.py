from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ai_investing.application.context import AppContext
from ai_investing.application.notifications import NotificationService
from ai_investing.application.scheduling import compute_initial_next_run_at, compute_next_run_at
from ai_investing.config.models import AgentConfig, PanelConfig
from ai_investing.domain.enums import (
    AlertLevel,
    CompanyType,
    GateDecision,
    MemoSectionStatus,
    RefreshJobStatus,
    RunContinueAction,
    RunKind,
    RunStatus,
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
    PanelSupportAssessment,
    PanelVerdict,
    ReviewQueueEntry,
    RunCheckpoint,
    RunRecord,
    SkippedPanelResult,
    StructuredGenerationRequest,
    new_id,
    utc_now,
)
from ai_investing.domain.read_models import PanelRunRead
from ai_investing.ingestion.base import ConnectorIngestRequest
from ai_investing.ingestion.registry import SourceConnectorRegistry
from ai_investing.monitoring import MonitoringDeltaService
from ai_investing.persistence.repositories import Repository

_MISSING_BASELINE = object()
_UNSET = object()
DEFAULT_CONNECTOR_IDS = {
    CompanyType.PUBLIC: "public_file_connector",
    CompanyType.PRIVATE: "private_file_connector",
}
EVIDENCE_FAMILY_ALIASES = {
    "core_company_documents": {"regulatory", "transcript", "dataroom"},
    "filings": {"regulatory"},
    "transcripts": {"transcript"},
    "dataroom": {"dataroom"},
    "kpi_reporting": {"kpi_packet"},
    "management_materials": {"dataroom"},
    "financial_statements": {"regulatory", "kpi_packet", "dataroom"},
    "market_data": {"market", "news", "ownership"},
    "regulatory_intelligence": {"regulatory", "news"},
    "consensus_views": {"consensus"},
    "milestone_tracking": {"events"},
    "security_context": {"ownership", "market"},
    "deal_context": {"dataroom"},
    "portfolio_context": {"portfolio_context"},
}
SOURCE_TYPE_EVIDENCE_FAMILIES = {
    "regulatory_filing": {"regulatory"},
    "earnings_call": {"transcript"},
    "public_news": {"news"},
    "board_deck": {"dataroom"},
    "diligence_note": {"dataroom"},
    "kpi_workbook": {"kpi_packet"},
    "market_snapshot": {"market"},
    "market_commentary": {"market"},
    "consensus_snapshot": {"consensus"},
    "ownership_report": {"ownership"},
    "ownership_flow": {"ownership"},
    "event_page": {"events"},
    "event_image": {"events"},
    "live_market_snapshot": {"market"},
}


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

    def list_cadence_policies(self) -> dict[str, Any]:
        registry = self.context.registries.cadence_policies
        return registry.model_dump(mode="json")

    def add_coverage(self, entry: CoverageEntry) -> CoverageEntry:
        if entry.next_run_at is None:
            entry.next_run_at = compute_initial_next_run_at(
                self.context.registries.cadence_policies,
                entry,
                now=utc_now(),
                preserve_legacy_weekly_due_now=(
                    entry.schedule_enabled
                    and entry.schedule_policy_id in {None, "weekly"}
                    and entry.preferred_run_time is None
                ),
            )
        with self.context.database.session() as session:
            repository = Repository(session)
            return repository.upsert_coverage(entry)

    def set_schedule(
        self,
        company_id: str,
        *,
        schedule_policy_id: str | object = _UNSET,
        schedule_enabled: bool | object = _UNSET,
        preferred_run_time: str | None | object = _UNSET,
    ) -> CoverageEntry:
        with self.context.database.session() as session:
            repository = Repository(session)
            entry = repository.get_coverage(company_id)
            if entry is None:
                raise KeyError(company_id)

            payload = entry.model_dump(mode="python")
            if schedule_policy_id is not _UNSET:
                payload["schedule_policy_id"] = schedule_policy_id
            if schedule_enabled is not _UNSET:
                payload["schedule_enabled"] = schedule_enabled
            if preferred_run_time is not _UNSET:
                payload["preferred_run_time"] = preferred_run_time

            updated = CoverageEntry.model_validate(payload)
            updated.next_run_at = (
                None
                if not updated.schedule_enabled
                else compute_initial_next_run_at(
                    self.context.registries.cadence_policies,
                    updated,
                    now=utc_now(),
                    preserve_legacy_weekly_due_now=False,
                )
            )
            return repository.upsert_coverage(updated)

    def list_coverage(self) -> list[CoverageEntry]:
        with self.context.database.session() as session:
            repository = Repository(session)
            return repository.list_coverage()

    def set_next_run_at(self, company_id: str, next_run_at: datetime | None) -> CoverageEntry:
        with self.context.database.session() as session:
            repository = Repository(session)
            entry = repository.get_coverage(company_id)
            if entry is None:
                raise KeyError(company_id)
            entry.next_run_at = next_run_at
            return repository.upsert_coverage(entry)

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
            if repository.get_coverage(company_id) is None:
                raise KeyError(company_id)
            repository.remove_coverage(company_id)


@dataclass
class IngestionService:
    context: AppContext

    def ingest_public_data(
        self,
        input_dir: Path,
        *,
        connector_id: str | None = None,
    ) -> tuple[CompanyProfile, list[str]]:
        return self._ingest(
            ConnectorIngestRequest(
                company_type=CompanyType.PUBLIC,
                input_dir=input_dir,
                connector_id=connector_id,
            )
        )

    def ingest_private_data(
        self,
        input_dir: Path,
        *,
        connector_id: str | None = None,
    ) -> tuple[CompanyProfile, list[str]]:
        return self._ingest(
            ConnectorIngestRequest(
                company_type=CompanyType.PRIVATE,
                input_dir=input_dir,
                connector_id=connector_id,
            )
        )

    def _ingest(self, request: ConnectorIngestRequest) -> tuple[CompanyProfile, list[str]]:
        connector = self._resolve_connector(request)
        profile, records = connector.ingest(request)
        if profile.company_type != request.company_type:
            raise ValueError(
                f"Connector {connector.id} loaded "
                f"{profile.company_type.value} data for a "
                f"{request.company_type.value} workflow."
            )
        with self.context.database.session() as session:
            repository = Repository(session)
            repository.save_company_profile(profile)
            repository.save_evidence_records(records)
        return profile, [record.evidence_id for record in records]

    def _resolve_connector(self, request: ConnectorIngestRequest):
        connector_id = request.connector_id or DEFAULT_CONNECTOR_IDS[request.company_type]
        registry = SourceConnectorRegistry.from_configs(
            self.context.registries.source_connectors.connectors
        )
        connector = registry.resolve(connector_id)
        if not connector.supports_company_type(request.company_type):
            raise ValueError(
                f"Connector {connector_id} is configured for {connector.config.company_type} "
                f"companies, not {request.company_type.value}."
            )
        return connector


@dataclass
class RefreshRuntime:
    context: AppContext
    run: RunRecord
    coverage: CoverageEntry
    company_profile: CompanyProfile
    prior_memo: ICMemo | None
    prior_active_claims: list[ClaimCard]
    prior_active_verdicts: dict[str, PanelVerdict]
    current_sections: dict[str, MemoSection]
    current_claims: list[ClaimCard]
    current_verdicts: dict[str, PanelVerdict]
    current_skipped_panels: dict[str, SkippedPanelResult]
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
    ) -> RefreshRuntime:
        prior_memo = cls._baseline_memo_from_run(run, repository, company_profile.company_id)
        prior_active_claims = cls._baseline_claims_from_run(
            run,
            repository,
            company_profile.company_id,
        )
        prior_active_verdicts = cls._baseline_verdicts_from_run(
            run,
            repository,
            company_profile.company_id,
        )
        current_memo = repository.get_memo_for_run(company_profile.company_id, run.run_id)
        if current_memo is not None:
            current_sections = current_memo.section_map()
        elif prior_memo is not None:
            current_sections = prior_memo.section_map()
        else:
            current_sections = {}
        current_claims = repository.list_claim_cards(company_profile.company_id, run_id=run.run_id)
        current_verdicts = {
            verdict.panel_id: verdict
            for verdict in repository.list_panel_verdicts(
                company_profile.company_id,
                run_id=run.run_id,
            )
        }
        return cls(
            context=context,
            run=run,
            coverage=coverage,
            company_profile=company_profile,
            prior_memo=prior_memo,
            prior_active_claims=prior_active_claims,
            prior_active_verdicts=prior_active_verdicts,
            current_sections=current_sections,
            current_claims=current_claims,
            current_verdicts=current_verdicts,
            current_skipped_panels=cls._skipped_panels_from_run(run),
            current_delta=repository.get_latest_monitoring_delta(
                company_profile.company_id,
                run_id=run.run_id,
            ),
        )

    def execute_panel(self, panel_id: str) -> dict[str, Any]:
        with self.context.database.session() as session:
            repository = Repository(session)
            panel = self.context.get_panel(panel_id)
            evidence = repository.list_evidence(self.company_profile.company_id, panel_id=panel_id)
            support = self._evaluate_panel_support(panel=panel, evidence=evidence)
            self._record_panel_support_assessment(support)
            if support.status == "unsupported":
                skip = SkippedPanelResult(
                    panel_id=panel.id,
                    panel_name=panel.name,
                    company_type=self.company_profile.company_type,
                    reason_code=self._unsupported_reason_code(support),
                    reason=support.reason,
                    evidence_summary=support.evidence_summary,
                    evidence_count=support.evidence_count,
                    factor_coverage_ratio=support.factor_coverage_ratio,
                    available_evidence_families=support.available_evidence_families,
                    missing_evidence_families=support.missing_evidence_families,
                    required_context=support.required_context,
                    missing_context=support.missing_context,
                )
                self._record_skipped_panel(skip)
                return {
                    "claims": [],
                    "skip": skip.model_dump(mode="json"),
                    "support": support.model_dump(mode="json"),
                }
            specialist_claims = self._run_specialists(
                repository=repository,
                panel=panel,
                evidence=evidence,
            )
            verdict = self._run_judge(
                repository=repository,
                panel=panel,
                claims=specialist_claims,
                evidence=evidence,
            )
        self.current_claims.extend(specialist_claims)
        return {
            "claims": [claim.model_dump(mode="json") for claim in specialist_claims],
            "verdict": verdict.model_dump(mode="json"),
            "support": support.model_dump(mode="json"),
        }

    def update_memo_for_panel(self, panel_id: str) -> dict[str, Any]:
        if panel_id in self.current_skipped_panels:
            partial_memo = self._build_memo(is_partial=True)
            with self.context.database.session() as session:
                Repository(session).save_memo(partial_memo)
            return {
                "updates": [],
                "memo": partial_memo.model_dump(mode="json"),
            }
        verdict = self.current_verdicts[panel_id]
        panel_claims = [claim for claim in self.current_claims if claim.panel_id == panel_id]
        updates: list[MemoSectionUpdate] = []
        for section_id in verdict.affected_section_ids:
            label = self.context.memo_section_labels(self.coverage.memo_label_profile)[section_id]
            prior_text = (
                self.current_sections.get(section_id).content
                if section_id in self.current_sections
                else ""
            )
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
                        "support_assessment": (
                            self._support_assessment_by_panel()[panel_id].model_dump(mode="json")
                            if panel_id in self._support_assessment_by_panel()
                            else None
                        ),
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
            updates.append(update)

        partial_memo = self._build_memo(is_partial=True)
        with self.context.database.session() as session:
            repository = Repository(session)
            for update in updates:
                repository.save_memo_section_update(update)
            repository.save_memo(partial_memo)
        return {
            "updates": [update.model_dump(mode="json") for update in updates],
            "memo": partial_memo.model_dump(mode="json"),
        }

    def compute_monitoring_delta(self) -> MonitoringDelta:
        delta = MonitoringDeltaService.from_runtime(self).compute_delta()
        self._update_delta_section(delta)
        delta.changed_sections = sorted(
            set(delta.changed_sections).union({"what_changed_since_last_run"})
        )
        self.current_delta = delta
        with self.context.database.session() as session:
            Repository(session).save_monitoring_delta(delta)
        return delta

    def skip_monitoring_delta(self) -> MonitoringDelta:
        delta = MonitoringDeltaService.from_runtime(self).build_disabled_delta()
        self._update_delta_section(delta)
        self.current_delta = delta
        with self.context.database.session() as session:
            Repository(session).save_monitoring_delta(delta)
        return delta

    def reconcile_ic_memo(self) -> ICMemo:
        memo = self._build_memo(is_partial=False)
        with self.context.database.session() as session:
            Repository(session).save_memo(memo)
        return memo

    def auto_continue_gatekeeper(
        self,
        *,
        gatekeeper: GatekeeperVerdict,
        has_downstream_panels: bool,
    ) -> dict[str, Any]:
        checkpoint = RunCheckpoint(
            checkpoint_panel_id="gatekeepers",
            allowed_actions=(
                [RunContinueAction.STOP, RunContinueAction.CONTINUE]
                if has_downstream_panels
                else [RunContinueAction.STOP]
            ),
            provisional_required=False,
            note=self._checkpoint_note(gatekeeper.gate_decision, has_downstream_panels),
            resolved_at=utc_now(),
            resolution_action=RunContinueAction.CONTINUE,
        )
        self.run.gate_decision = gatekeeper.gate_decision
        self.run.awaiting_continue = False
        self.run.gated_out = False
        self.run.provisional = False
        self.run.stopped_after_panel = None
        self.run.checkpoint_panel_id = "gatekeepers"
        self.run.checkpoint = checkpoint
        self.run.status = RunStatus.RUNNING
        with self.context.database.session() as session:
            Repository(session).save_run(self.run)
        return {
            "gate_decision": gatekeeper.gate_decision.value,
            "awaiting_continue": False,
            "gated_out": False,
            "provisional": False,
            "stopped_after_panel": None,
            "checkpoint_panel_id": self.run.checkpoint_panel_id,
            "resume_action": RunContinueAction.CONTINUE.value,
        }

    def prepare_gatekeeper_checkpoint(
        self,
        *,
        gatekeeper: GatekeeperVerdict,
        has_downstream_panels: bool,
    ) -> RunCheckpoint:
        allowed_actions = [RunContinueAction.STOP]
        if has_downstream_panels:
            allowed_actions.append(
                RunContinueAction.CONTINUE_PROVISIONAL
                if gatekeeper.gate_decision == GateDecision.FAIL
                else RunContinueAction.CONTINUE
            )
        checkpoint = RunCheckpoint(
            checkpoint_panel_id="gatekeepers",
            allowed_actions=allowed_actions,
            provisional_required=gatekeeper.gate_decision == GateDecision.FAIL,
            note=self._checkpoint_note(gatekeeper.gate_decision, has_downstream_panels),
        )
        self.run.gate_decision = gatekeeper.gate_decision
        self.run.awaiting_continue = True
        self.run.gated_out = False
        self.run.provisional = False
        self.run.stopped_after_panel = None
        self.run.checkpoint_panel_id = "gatekeepers"
        self.run.checkpoint = checkpoint
        self.run.status = RunStatus.AWAITING_CONTINUE
        with self.context.database.session() as session:
            Repository(session).save_run(self.run)
        return checkpoint

    def resolve_gatekeeper_action(
        self,
        *,
        action: RunContinueAction,
        gatekeeper: GatekeeperVerdict,
        has_downstream_panels: bool,
    ) -> dict[str, Any]:
        if action != RunContinueAction.STOP and not has_downstream_panels:
            raise ValueError("No downstream panels remain after gatekeepers.")
        if gatekeeper.gate_decision == GateDecision.FAIL and action == RunContinueAction.CONTINUE:
            raise ValueError("Failed gatekeepers can only resume as provisional analysis.")

        self.run.gate_decision = gatekeeper.gate_decision
        self.run.awaiting_continue = False
        self.run.gated_out = (
            action == RunContinueAction.STOP and gatekeeper.gate_decision == GateDecision.FAIL
        )
        self.run.provisional = action == RunContinueAction.CONTINUE_PROVISIONAL
        self.run.stopped_after_panel = "gatekeepers" if action == RunContinueAction.STOP else None
        self.run.checkpoint_panel_id = "gatekeepers"
        self.run.status = RunStatus.RUNNING
        if self.run.checkpoint is not None:
            self.run.checkpoint = self.run.checkpoint.model_copy(
                update={
                    "resolved_at": utc_now(),
                    "resolution_action": action,
                }
            )
        with self.context.database.session() as session:
            Repository(session).save_run(self.run)
        return {
            "gate_decision": gatekeeper.gate_decision.value,
            "awaiting_continue": False,
            "gated_out": self.run.gated_out,
            "provisional": self.run.provisional,
            "stopped_after_panel": self.run.stopped_after_panel,
            "checkpoint_panel_id": self.run.checkpoint_panel_id,
            "resume_action": action.value,
        }

    def _run_specialists(
        self,
        *,
        repository: Repository,
        panel: PanelConfig,
        evidence: list[Any],
    ) -> list[ClaimCard]:
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
                    repository=repository,
                    agent=agent,
                    company_id=self.company_profile.company_id,
                    run_id=self.run.run_id,
                    tool_id="evidence_search",
                    payload={"panel_id": panel.id, "factor_id": factor_id},
                )["records"]
                prior_claims = self.context.tool_registry.execute(
                    repository=repository,
                    agent=agent,
                    company_id=self.company_profile.company_id,
                    run_id=self.run.run_id,
                    tool_id="claim_search",
                    payload={"panel_id": panel.id, "factor_id": factor_id, "active_only": True},
                )["claims"]
                prompt = self.context.prompt_loader.load(agent.prompt_path)
                provider = self.context.get_provider(agent.model_profile)
                claim = provider.generate_structured(
                    StructuredGenerationRequest(
                        task_type="claim_card",
                        prompt=prompt,
                        input_data=self._build_agent_input_data(
                            agent=agent,
                            panel=panel,
                            namespace=f"company/{self.company_profile.company_id}/claims/{factor_id}",
                            factor_id=factor_id,
                            factor_name=factor_name,
                            evidence=tool_evidence,
                            prior_claims=prior_claims,
                        ),
                    ),
                    ClaimCard,
                )
                claims.append(claim)
        repository.save_claim_cards(claims)
        return claims

    def _run_judge(
        self,
        *,
        repository: Repository,
        panel: PanelConfig,
        claims: list[ClaimCard],
        evidence: list[Any],
    ) -> PanelVerdict:
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
                input_data=self._build_agent_input_data(
                    agent=judge,
                    panel=panel,
                    namespace=f"company/{self.company_profile.company_id}/verdicts/{panel.id}",
                    evidence=evidence,
                    claims=claims,
                ),
            ),
            response_model,
        )
        repository.save_panel_verdict(verdict)
        return verdict

    def finalize_panel_verdict(
        self,
        *,
        panel_id: str,
        verdict: PanelVerdict,
        support_payload: dict[str, Any] | None = None,
    ) -> PanelVerdict:
        panel = self.context.get_panel(panel_id)
        support = (
            PanelSupportAssessment.model_validate(support_payload)
            if support_payload is not None
            else None
        )
        lead_agents = [
            agent
            for agent in self.context.active_agents_for_panel(panel.id)
            if agent.role_type == "lead"
        ]
        updated = verdict
        if lead_agents:
            lead = lead_agents[0]
            provider = self.context.get_provider(lead.model_profile)
            prompt = self.context.prompt_loader.load(lead.prompt_path)
            panel_claims = [claim for claim in self.current_claims if claim.panel_id == panel_id]
            response_model = GatekeeperVerdict if panel.id == "gatekeepers" else PanelVerdict
            updated = provider.generate_structured(
                StructuredGenerationRequest(
                    task_type="panel_lead",
                    prompt=prompt,
                    input_data=self._build_agent_input_data(
                        agent=lead,
                        panel=panel,
                        namespace=f"company/{self.company_profile.company_id}/verdicts/{panel.id}",
                        claims=panel_claims,
                        verdict=verdict,
                        support=support,
                    )
                    | {"supersedes_verdict_id": verdict.verdict_id},
                ),
                response_model,
            )
            updated = updated.model_copy(
                update={
                    "verdict_id": new_id("vrd"),
                    "supersedes_verdict_id": verdict.verdict_id,
                }
            )
        if support is not None and support.status == "weak_confidence":
            updated = self._apply_weak_confidence_posture(updated, support)
        with self.context.database.session() as session:
            Repository(session).save_panel_verdict(updated)
        self.current_verdicts[panel_id] = updated
        return updated

    def _build_agent_input_data(
        self,
        *,
        agent: AgentConfig,
        panel: PanelConfig,
        namespace: str,
        factor_id: str | None = None,
        factor_name: str | None = None,
        evidence: list[Any] | None = None,
        prior_claims: list[dict[str, Any]] | None = None,
        claims: list[ClaimCard] | None = None,
        verdict: PanelVerdict | None = None,
        support: PanelSupportAssessment | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "company_id": self.company_profile.company_id,
            "company_name": self.company_profile.company_name,
            "company_type": self.company_profile.company_type.value,
            "run_id": self.run.run_id,
            "panel_id": panel.id,
            "panel_name": panel.name,
            "agent_id": agent.id,
            "role_type": agent.role_type,
            "section_ids": panel.memo_section_ids,
            "affected_section_ids": panel.memo_section_ids,
            "namespace": namespace,
        }
        if factor_id is not None:
            payload["factor_id"] = factor_id
        if factor_name is not None:
            payload["factor_name"] = factor_name

        channel_set = set(agent.input_channels)
        if "evidence" in channel_set:
            payload["evidence"] = list(evidence or [])
        if "prior_claims" in channel_set:
            prior_claims = list(prior_claims or [])
            payload["prior_claims"] = prior_claims
            payload["prior_claim"] = prior_claims[0]["claim"] if prior_claims else ""
        if "prior_memo" in channel_set:
            payload["prior_memo"] = (
                self.prior_memo.model_dump(mode="json") if self.prior_memo is not None else None
            )
        if "claims" in channel_set:
            payload["claims"] = [
                claim.model_dump(mode="json") if isinstance(claim, ClaimCard) else claim
                for claim in (claims or [])
            ]
        if "panel_verdict" in channel_set and verdict is not None:
            payload["panel_verdict"] = verdict.model_dump(mode="json")
        if "panel_verdicts" in channel_set:
            payload["panel_verdicts"] = [
                item.model_dump(mode="json") for item in self.current_verdicts.values()
            ]
        if "memo_sections" in channel_set:
            payload["memo_sections"] = [
                section.model_dump(mode="json") for section in self.current_sections.values()
            ]
        if "prior_run" in channel_set:
            payload["prior_run"] = self._prior_run_payload()
        if support is not None:
            payload["support_assessment"] = support.model_dump(mode="json")
        return payload

    def _evaluate_panel_support(
        self,
        *,
        panel: PanelConfig,
        evidence: list[Any],
    ) -> PanelSupportAssessment:
        company_type = self.company_profile.company_type.value
        evidence_families = self._evidence_families(evidence)
        factor_coverage_ratio = self._factor_coverage_ratio(panel=panel, evidence=evidence)
        evidence_count = len(evidence)
        readiness = panel.readiness
        support = panel.support
        required_families = readiness.required_evidence_families.get(company_type, [])
        missing_families = [
            family
            for family in required_families
            if not (EVIDENCE_FAMILY_ALIASES.get(family, {family}) & evidence_families)
        ]
        required_context = list(readiness.required_context)
        available_context = self._available_context_keys()
        missing_context = [item for item in required_context if item not in available_context]

        weak_confidence = support.weak_confidence
        weak_threshold_met = (
            weak_confidence.enabled
            and weak_confidence.minimum_factor_coverage_ratio is not None
            and weak_confidence.minimum_evidence_count is not None
            and factor_coverage_ratio >= weak_confidence.minimum_factor_coverage_ratio
            and evidence_count >= weak_confidence.minimum_evidence_count
        )
        fully_supported = (
            company_type in support.required_company_types
            and not missing_context
            and not missing_families
            and factor_coverage_ratio >= readiness.minimum_factor_coverage_ratio
            and evidence_count >= readiness.minimum_evidence_count
        )

        status = "supported"
        reason = "Panel support requirements are satisfied for this run."
        if not fully_supported:
            if (
                missing_context
                or missing_families
                or company_type not in support.required_company_types
            ):
                status = "unsupported"
            elif weak_threshold_met:
                status = "weak_confidence"
            else:
                status = "unsupported"
            reason = self._support_reason(
                panel=panel,
                company_type=company_type,
                missing_context=missing_context,
                missing_families=missing_families,
                factor_coverage_ratio=factor_coverage_ratio,
                evidence_count=evidence_count,
            )

        return PanelSupportAssessment(
            panel_id=panel.id,
            panel_name=panel.name,
            company_type=self.company_profile.company_type,
            status=status,
            reason=reason,
            evidence_count=evidence_count,
            factor_coverage_ratio=round(factor_coverage_ratio, 2),
            evidence_summary=self._evidence_summary(
                evidence_count,
                evidence_families,
                factor_coverage_ratio,
            ),
            available_evidence_families=sorted(evidence_families),
            missing_evidence_families=missing_families,
            required_context=required_context,
            missing_context=missing_context,
            weak_confidence_allowed=weak_confidence.enabled,
        )

    def _apply_weak_confidence_posture(
        self,
        verdict: PanelVerdict,
        support: PanelSupportAssessment,
    ) -> PanelVerdict:
        concerns = list(dict.fromkeys([*verdict.concerns, support.reason]))
        return verdict.model_copy(
            update={
                "verdict_id": new_id("vrd"),
                "summary": self._append_content(
                    verdict.summary,
                    "Weak-confidence read due to thin evidence.",
                ),
                "confidence": round(min(verdict.confidence, 0.45), 2),
                "concerns": concerns,
                "supersedes_verdict_id": verdict.verdict_id,
            }
        )

    def _record_panel_support_assessment(self, support: PanelSupportAssessment) -> None:
        assessments = [
            PanelSupportAssessment.model_validate(item)
            for item in self.run.metadata.get("panel_support_assessments", [])
        ]
        assessments = [item for item in assessments if item.panel_id != support.panel_id]
        assessments.append(support)
        self.run.metadata = {
            **self.run.metadata,
            "panel_support_assessments": [
                item.model_dump(mode="json") for item in assessments
            ],
        }

    def _record_skipped_panel(self, skip: SkippedPanelResult) -> None:
        self.current_skipped_panels[skip.panel_id] = skip
        skipped_panels = list(self.current_skipped_panels.values())
        self.run.metadata = {
            **self.run.metadata,
            "skipped_panels": [item.model_dump(mode="json") for item in skipped_panels],
        }

    def _available_context_keys(self) -> set[str]:
        raw_context = self.run.metadata.get("available_context", [])
        available = {str(item) for item in raw_context if isinstance(item, str)}
        if self.prior_memo is not None:
            available.add("prior_memo")
        if self.prior_active_verdicts:
            available.add("prior_run")
        if self.current_verdicts:
            available.add("panel_verdicts")
        return available

    @staticmethod
    def _evidence_families(evidence: list[Any]) -> set[str]:
        families: set[str] = set()
        for record in evidence:
            metadata = getattr(record, "metadata", {}) or {}
            family = metadata.get("evidence_family")
            if isinstance(family, str) and family.strip():
                families.add(family.strip())
                continue
            source_type = getattr(record, "source_type", None)
            if isinstance(source_type, str):
                families.update(SOURCE_TYPE_EVIDENCE_FAMILIES.get(source_type, set()))
        return families

    @staticmethod
    def _factor_coverage_ratio(*, panel: PanelConfig, evidence: list[Any]) -> float:
        if not panel.factor_ids:
            return 1.0
        covered_factors: set[str] = set()
        for record in evidence:
            covered_factors.update(
                factor_id
                for factor_id in getattr(record, "factor_ids", [])
                if factor_id in panel.factor_ids
            )
        return len(covered_factors) / len(panel.factor_ids)

    @staticmethod
    def _evidence_summary(
        evidence_count: int,
        evidence_families: set[str],
        factor_coverage_ratio: float,
    ) -> str:
        families = ", ".join(sorted(evidence_families)) if evidence_families else "none"
        return (
            f"{evidence_count} records matched this panel; evidence families: {families}; "
            f"factor coverage ratio: {factor_coverage_ratio:.2f}."
        )

    def _support_reason(
        self,
        *,
        panel: PanelConfig,
        company_type: str,
        missing_context: list[str],
        missing_families: list[str],
        factor_coverage_ratio: float,
        evidence_count: int,
    ) -> str:
        if company_type not in panel.support.required_company_types:
            return (
                f"{panel.name} is not configured for {company_type} runs."
            )
        if missing_context:
            return (
                f"{panel.name} requires run context that is missing: "
                f"{', '.join(missing_context)}."
            )
        if missing_families:
            return (
                f"{panel.name} is missing required evidence families for this run: "
                f"{', '.join(missing_families)}."
            )
        return (
            f"{panel.name} has only {evidence_count} supporting records with "
            f"{factor_coverage_ratio:.2f} factor coverage against a "
            f"{panel.readiness.minimum_factor_coverage_ratio:.2f} readiness bar."
        )

    @staticmethod
    def _unsupported_reason_code(support: PanelSupportAssessment) -> str:
        if support.missing_context:
            return "missing_context"
        if support.missing_evidence_families:
            return "missing_evidence_families"
        return "insufficient_evidence"

    def _prior_run_payload(self) -> dict[str, Any] | None:
        if self.prior_memo is None and not self.prior_active_verdicts:
            return None
        return {
            "memo_id": self.prior_memo.memo_id if self.prior_memo is not None else None,
            "run_id": self.prior_memo.run_id if self.prior_memo is not None else None,
            "panel_ids": sorted(self.prior_active_verdicts),
        }

    def _support_assessment_by_panel(self) -> dict[str, PanelSupportAssessment]:
        raw_items = self.run.metadata.get("panel_support_assessments", [])
        if not isinstance(raw_items, list):
            return {}
        assessments = [PanelSupportAssessment.model_validate(item) for item in raw_items]
        return {item.panel_id: item for item in assessments}

    def _apply_section_truthfulness_notes(
        self,
        *,
        section_id: str,
        content: str,
        status: MemoSectionStatus,
    ) -> str:
        weak_panels = [
            assessment.panel_name
            for panel_id, assessment in self._support_assessment_by_panel().items()
            if assessment.status == "weak_confidence"
            and panel_id in self.current_verdicts
            and section_id in self.context.get_panel(panel_id).memo_section_ids
        ]
        if weak_panels and status == MemoSectionStatus.REFRESHED:
            content = self._prefix_content(
                content,
                f"Weak-confidence support this run: {', '.join(sorted(weak_panels))}.",
            )

        skipped_panels = [
            skip
            for skip in self.current_skipped_panels.values()
            if section_id in self.context.get_panel(skip.panel_id).memo_section_ids
        ]
        if skipped_panels and status != MemoSectionStatus.REFRESHED:
            panel_text = "; ".join(
                f"{skip.panel_name} ({skip.reason_code.replace('_', ' ')})"
                for skip in skipped_panels
            )
            content = self._prefix_content(content, f"Skipped this run: {panel_text}.")

        if section_id == "overall_recommendation":
            note = self._overall_recommendation_truthfulness_note()
            if note:
                content = self._prefix_content(content, note)
        return content

    def _overall_recommendation_truthfulness_note(self) -> str | None:
        selected_panel_ids = self._selected_panel_ids()
        notes: list[str] = []
        overlay_labels = {
            "security_or_deal_overlay": "security or deal overlay",
            "portfolio_fit_positioning": "portfolio fit positioning",
        }
        for panel_id, label in overlay_labels.items():
            if panel_id not in selected_panel_ids:
                notes.append(f"{label} pending for this rollout")
            elif panel_id in self.current_skipped_panels:
                notes.append(f"{label} unsupported for this run")
        if not notes:
            return None
        return (
            "Overall recommendation reflects company-quality panels only; "
            + "; ".join(notes)
            + "."
        )

    def _selected_panel_ids(self) -> set[str]:
        panel_ids = self.run.metadata.get("panel_ids", [])
        if not isinstance(panel_ids, list):
            return set()
        return {str(panel_id) for panel_id in panel_ids}

    def _build_memo(self, *, is_partial: bool) -> ICMemo:
        labels = self.context.memo_section_labels(self.coverage.memo_label_profile)
        gatekeeper_section_ids = self._gatekeeper_section_ids()
        ordered_sections: list[MemoSection] = []
        for section_id, label in labels.items():
            ordered_sections.append(
                self._project_memo_section(
                    section_id=section_id,
                    label=label,
                    gatekeeper_section_ids=gatekeeper_section_ids,
                    is_partial=is_partial,
                )
            )
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
                    "is_partial": is_partial,
                    "gate_decision": (
                        self._current_gate_decision().value
                        if self._current_gate_decision() is not None
                        else None
                    ),
                    "awaiting_continue": self.run.awaiting_continue,
                    "provisional": self.run.provisional,
                    "stopped_after_panel": self.run.stopped_after_panel,
                },
            ),
            ICMemo,
        )

    def _project_memo_section(
        self,
        *,
        section_id: str,
        label: str,
        gatekeeper_section_ids: set[str],
        is_partial: bool,
    ) -> MemoSection:
        section = self.current_sections.get(section_id)
        if section is None:
            return MemoSection(
                section_id=section_id,
                label=label,
                content=self._default_section_content(
                    section_id=section_id,
                    gatekeeper_section_ids=gatekeeper_section_ids,
                    is_partial=is_partial,
                ),
                status=MemoSectionStatus.NOT_ADVANCED,
            )

        if section.updated_by_run_id == self.run.run_id:
            status = MemoSectionStatus.REFRESHED
        elif self._is_same_run_placeholder_section(section):
            status = MemoSectionStatus.NOT_ADVANCED
        else:
            status = MemoSectionStatus.STALE
        if status == MemoSectionStatus.STALE and not section.content:
            status = MemoSectionStatus.NOT_ADVANCED

        content = section.content or self._default_section_content(
            section_id=section_id,
            gatekeeper_section_ids=gatekeeper_section_ids,
            is_partial=is_partial,
        )
        if status == MemoSectionStatus.STALE:
            content = self._stale_section_content(
                section_id=section_id,
                content=content,
                gatekeeper_section_ids=gatekeeper_section_ids,
                is_partial=is_partial,
            )
        content = self._apply_section_truthfulness_notes(
            section_id=section_id,
            content=content,
            status=status,
        )
        if self.run.provisional and status == MemoSectionStatus.REFRESHED:
            content = self._prefix_content(
                content,
                "Provisional after failed gatekeeper override.",
            )

        return section.model_copy(
            update={
                "label": label,
                "content": content,
                "status": status,
            }
        )

    def _default_section_content(
        self,
        *,
        section_id: str,
        gatekeeper_section_ids: set[str],
        is_partial: bool,
    ) -> str:
        if section_id == "what_changed_since_last_run":
            if self.prior_memo is None:
                return (
                    "No prior active run exists yet, so the run-log delta section is "
                    "not advanced."
                )
            return "This run has not advanced the run-log delta section yet."

        gatekeeper_only = self._is_gatekeeper_only_projection(is_partial=is_partial)
        gate_decision = self._current_gate_decision()
        if gatekeeper_only and section_id not in gatekeeper_section_ids:
            if gate_decision == GateDecision.FAIL:
                return (
                    "Gatekeepers blocked deeper panel work this run, so this section has not "
                    "been advanced yet."
                )
            return (
                "Gatekeepers completed this run, but deeper panel work has not advanced this "
                "section yet."
            )
        return "This section has not been advanced yet."

    def _stale_section_content(
        self,
        *,
        section_id: str,
        content: str,
        gatekeeper_section_ids: set[str],
        is_partial: bool,
    ) -> str:
        if self._is_gatekeeper_only_projection(is_partial=is_partial):
            if section_id == "what_changed_since_last_run":
                return self._prefix_content(
                    content,
                    "Carried forward from the prior memo until this run completes monitoring.",
                )
            if section_id not in gatekeeper_section_ids:
                gate_decision = self._current_gate_decision()
                prefix = (
                    "Carried forward from the prior memo because gatekeepers blocked deeper "
                    "refresh work this run."
                    if gate_decision == GateDecision.FAIL
                    else "Carried forward from the prior memo because deeper panel work has not "
                    "refreshed this section yet."
                )
                return self._prefix_content(content, prefix)
        return self._prefix_content(content, "Stale from the prior active memo.")

    @staticmethod
    def _prefix_content(content: str, prefix: str) -> str:
        if content.startswith(prefix):
            return content
        return f"{prefix} {content}".strip()

    @staticmethod
    def _append_content(content: str, suffix: str) -> str:
        if content.endswith(suffix):
            return content
        return f"{content} {suffix}".strip()

    def _current_gate_decision(self) -> GateDecision | None:
        if self.run.gate_decision is not None:
            return self.run.gate_decision
        verdict = self.current_verdicts.get("gatekeepers")
        if isinstance(verdict, GatekeeperVerdict):
            return verdict.gate_decision
        return None

    def _gatekeeper_section_ids(self) -> set[str]:
        try:
            return set(self.context.get_panel("gatekeepers").memo_section_ids)
        except KeyError:
            return set()

    def _is_gatekeeper_only_projection(self, *, is_partial: bool) -> bool:
        if "gatekeepers" not in self.current_verdicts:
            return False
        if set(self.current_verdicts) != {"gatekeepers"}:
            return False
        return (
            is_partial
            or self.run.awaiting_continue
            or self.run.stopped_after_panel == "gatekeepers"
        )

    def _is_same_run_placeholder_section(self, section: MemoSection) -> bool:
        return (
            self.prior_memo is None
            and section.updated_by_run_id is None
            and section.status == MemoSectionStatus.NOT_ADVANCED
        )

    def _update_delta_section(self, delta: MonitoringDelta) -> None:
        label = self.context.memo_section_labels(self.coverage.memo_label_profile)[
            "what_changed_since_last_run"
        ]
        if self.prior_memo is None:
            content = "Initial coverage run. No prior memo exists."
        else:
            changed = (
                ", ".join(delta.changed_sections) if delta.changed_sections else "no memo sections"
            )
            content = f"{delta.change_summary} Changed sections: {changed}."
        self.current_sections["what_changed_since_last_run"] = MemoSection(
            section_id="what_changed_since_last_run",
            label=label,
            content=content,
            status=MemoSectionStatus.REFRESHED,
            updated_by_run_id=self.run.run_id,
        )

    @staticmethod
    def _baseline_memo_from_run(
        run: RunRecord,
        repository: Repository,
        company_id: str,
    ) -> ICMemo | None:
        baseline = run.metadata.get("baseline_memo", _MISSING_BASELINE)
        if baseline is not _MISSING_BASELINE:
            if baseline in (None, {}, []):
                return None
            return ICMemo.model_validate(baseline)
        return repository.get_latest_memo_excluding_run(company_id, run_id=run.run_id)

    @staticmethod
    def _baseline_claims_from_run(
        run: RunRecord,
        repository: Repository,
        company_id: str,
    ) -> list[ClaimCard]:
        baseline_claims = run.metadata.get("baseline_active_claims", _MISSING_BASELINE)
        if baseline_claims is not _MISSING_BASELINE:
            if baseline_claims in (None, {}, []):
                return []
            return [ClaimCard.model_validate(claim) for claim in baseline_claims]
        return repository.list_latest_claim_cards_excluding_run(company_id, run_id=run.run_id)

    @staticmethod
    def _baseline_verdicts_from_run(
        run: RunRecord,
        repository: Repository,
        company_id: str,
    ) -> dict[str, PanelVerdict]:
        baseline_verdicts = run.metadata.get("baseline_active_verdicts", _MISSING_BASELINE)
        if baseline_verdicts is not _MISSING_BASELINE:
            if baseline_verdicts in (None, {}, []):
                return {}
            verdicts = (
                GatekeeperVerdict.model_validate(verdict)
                if "gate_decision" in verdict
                else PanelVerdict.model_validate(verdict)
                for verdict in baseline_verdicts
            )
            return {verdict.panel_id: verdict for verdict in verdicts}
        return {
            verdict.panel_id: verdict
            for verdict in repository.list_latest_panel_verdicts_excluding_run(
                company_id,
                run_id=run.run_id,
            )
        }

    @staticmethod
    def _skipped_panels_from_run(run: RunRecord) -> dict[str, SkippedPanelResult]:
        raw_items = run.metadata.get("skipped_panels", [])
        if not isinstance(raw_items, list):
            return {}
        skipped = [SkippedPanelResult.model_validate(item) for item in raw_items]
        return {item.panel_id: item for item in skipped}

    def _delta_thresholds(self) -> dict[str, Any]:
        return dict(self.context.registries.monitoring.monitoring.delta_thresholds)

    def _threshold_string_set(self, key: str) -> set[str]:
        value = self._delta_thresholds().get(key, [])
        if not isinstance(value, list):
            return set()
        return {str(item) for item in value}

    @staticmethod
    def _claim_change_is_material(
        *,
        prior_claim: ClaimCard | None,
        claim: ClaimCard,
        confidence_materiality: float,
    ) -> bool:
        if prior_claim is None:
            return True
        meaning_changed = any(
            (
                prior_claim.claim != claim.claim,
                prior_claim.bull_case != claim.bull_case,
                prior_claim.bear_case != claim.bear_case,
                prior_claim.staleness_assessment != claim.staleness_assessment,
                prior_claim.time_horizon != claim.time_horizon,
                prior_claim.durability_horizon != claim.durability_horizon,
            )
        )
        confidence_changed = (
            abs(prior_claim.confidence - claim.confidence) >= confidence_materiality
        )
        return meaning_changed or confidence_changed

    @staticmethod
    def _drift_flags_for_claim_change(claim: ClaimCard) -> set[str]:
        flags: set[str] = set()
        if claim.factor_id == "customer_concentration":
            flags.add("concentration_increase")
        if claim.factor_id == "balance_sheet_survivability":
            flags.add("survivability_deterioration")
        if claim.factor_id == "revenue_recurrence_contract_strength":
            flags.add("weakening_recurrence")
        if claim.factor_id == "governance_investability":
            flags.add("governance_risk_increase")
        return flags

    def _section_change_is_material(
        self,
        *,
        section_id: str,
        section: MemoSection,
        materially_impacted_sections: set[str],
    ) -> bool:
        if self.prior_memo is None:
            return section.updated_by_run_id == self.run.run_id
        prior_section = self.prior_memo.section_map().get(section_id)
        if prior_section is None:
            return section.updated_by_run_id == self.run.run_id
        if section.status != prior_section.status:
            return True
        return section_id in materially_impacted_sections

    def _verdict_changed_sections(self) -> set[str]:
        changed_sections: set[str] = set()
        for panel_id, verdict in self.current_verdicts.items():
            prior_verdict = self.prior_active_verdicts.get(panel_id)
            if prior_verdict is None:
                changed_sections.update(verdict.affected_section_ids)
                continue
            if verdict.recommendation != prior_verdict.recommendation:
                changed_sections.update(verdict.affected_section_ids)
        return changed_sections

    def _gatekeeper_decision_changed(self) -> bool:
        prior_verdict = self.prior_active_verdicts.get("gatekeepers")
        current_verdict = self.current_verdicts.get("gatekeepers")
        if not isinstance(prior_verdict, GatekeeperVerdict):
            return False
        if not isinstance(current_verdict, GatekeeperVerdict):
            return False
        return prior_verdict.gate_decision != current_verdict.gate_decision

    def _monitoring_change_summary(
        self,
        *,
        changed_claim_ids: list[str],
        changed_sections: list[str],
        drift_flags: set[str],
        gate_decision_changed: bool,
    ) -> str:
        if (
            not changed_claim_ids
            and not changed_sections
            and not drift_flags
            and not gate_decision_changed
        ):
            return (
                f"{self.company_profile.company_name} reran with no material thesis change. "
                "Refreshed the run log only."
            )

        parts = [f"{self.company_profile.company_name} rerun detected thesis movement."]
        if gate_decision_changed:
            parts.append("Gatekeeper decision changed.")
        if changed_sections:
            parts.append(f"Material sections: {', '.join(sorted(changed_sections))}.")
        if changed_claim_ids:
            parts.append(f"Material claim cards: {len(changed_claim_ids)}.")
        if drift_flags:
            parts.append(f"Drift flags: {', '.join(sorted(drift_flags))}.")
        return " ".join(parts)

    @staticmethod
    def _delta_alert_level(
        *,
        changed_claim_ids: list[str],
        changed_sections: list[str],
        drift_flags: set[str],
        gate_decision_changed: bool,
        high_alert_sections: set[str],
        medium_alert_sections: set[str],
        high_alert_drift_flags: set[str],
        medium_alert_claim_change_count: int,
    ) -> AlertLevel:
        changed_section_set = set(changed_sections)
        if gate_decision_changed:
            return AlertLevel.HIGH
        if high_alert_sections.intersection(changed_section_set):
            return AlertLevel.HIGH
        if high_alert_drift_flags.intersection(drift_flags):
            return AlertLevel.HIGH
        if medium_alert_sections.intersection(changed_section_set):
            return AlertLevel.MEDIUM
        if drift_flags:
            return AlertLevel.MEDIUM
        if len(changed_claim_ids) >= medium_alert_claim_change_count:
            return AlertLevel.MEDIUM
        return AlertLevel.LOW

    @staticmethod
    def _checkpoint_note(gate_decision: GateDecision, has_downstream_panels: bool) -> str:
        if gate_decision == GateDecision.FAIL:
            if has_downstream_panels:
                return "Gatekeepers failed. Continue only as provisional downstream analysis."
            return "Gatekeepers failed. Finalize by stopping after this panel."
        if has_downstream_panels:
            if gate_decision == GateDecision.REVIEW:
                return "Gatekeepers flagged review and downstream panels continue automatically."
            return "Gatekeepers passed and downstream panels continue automatically."
        return "Gatekeepers completed with no downstream panels remaining."


@dataclass
class AnalysisService:
    context: AppContext

    def initialize_database(self) -> None:
        self.context.database.initialize()

    def analyze_company(
        self,
        company_id: str,
        panel_ids: list[str] | None = None,
        *,
        triggered_by: str = "operator",
    ) -> dict[str, Any]:
        return self._start_run(
            company_id=company_id,
            panel_ids=panel_ids,
            run_kind=RunKind.ANALYZE,
            triggered_by=triggered_by,
        )

    def refresh_company(
        self,
        company_id: str,
        *,
        job_id: str | None = None,
        triggered_by: str = "system",
    ) -> dict[str, Any]:
        return self._start_run(
            company_id=company_id,
            panel_ids=None,
            run_kind=RunKind.REFRESH,
            job_id=job_id,
            triggered_by=triggered_by,
        )

    def continue_run(
        self,
        run_id: str,
        action: RunContinueAction = RunContinueAction.CONTINUE,
    ) -> dict[str, Any]:
        with self.context.database.session() as session:
            repository = Repository(session)
            run = repository.get_run(run_id)
            if run is None:
                raise KeyError(run_id)
            if run.status != RunStatus.AWAITING_CONTINUE:
                raise ValueError(f"Run {run_id} is not awaiting continuation.")
        return self._execute_run(run_id=run_id, resume_action=action)

    def run_panel(self, company_id: str, panel_id: str) -> dict[str, Any]:
        return self._start_run(
            company_id=company_id,
            panel_ids=[panel_id],
            run_kind=RunKind.PANEL,
            triggered_by="operator",
        )

    def execute_refresh_job(self, job_id: str, *, worker_id: str) -> dict[str, Any]:
        with self.context.database.session() as session:
            repository = Repository(session)
            job = repository.get_refresh_job(job_id)
            if job is None:
                raise KeyError(job_id)
            if job.run_id is not None and job.status in {
                RefreshJobStatus.COMPLETE,
                RefreshJobStatus.REVIEW_REQUIRED,
            }:
                run = repository.get_run(job.run_id)
                if run is not None:
                    return self._build_persisted_result(repository, run)
        return self.refresh_company(
            job.company_id,
            job_id=job_id,
            triggered_by=f"worker:{worker_id}",
        )

    def run_due_coverage(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        with self.context.database.session() as session:
            repository = Repository(session)
            due_entries = repository.list_coverage(enabled_only=True, due_only=True, now=utc_now())
        for entry in due_entries:
            with self.context.database.session() as session:
                repository = Repository(session)
                latest_runs = repository.list_runs(entry.company_id)
                if latest_runs and latest_runs[0].status == RunStatus.AWAITING_CONTINUE:
                    results.append(self._build_persisted_result(repository, latest_runs[0]))
                    continue
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

    def _start_run(
        self,
        *,
        company_id: str,
        panel_ids: list[str] | None,
        run_kind: RunKind,
        job_id: str | None = None,
        triggered_by: str,
    ) -> dict[str, Any]:
        with self.context.database.session() as session:
            repository = Repository(session)
            coverage = repository.get_coverage(company_id)
            if coverage is None:
                raise KeyError(f"No coverage entry for {company_id}")
            company_profile = repository.get_company_profile(company_id)
            if company_profile is None:
                raise KeyError(f"No company profile for {company_id}")
            latest_runs = repository.list_runs(company_id)
            if latest_runs and latest_runs[0].status == RunStatus.AWAITING_CONTINUE:
                raise ValueError(
                    f"Run {latest_runs[0].run_id} is awaiting continuation. Resume it instead."
                )
            policy = self.context.registries.run_policies.run_policies[coverage.panel_policy]
            selected_panels = self._resolve_panel_ids(
                coverage=coverage,
                panel_ids=panel_ids,
                run_kind=run_kind,
            )
            prior_memo = repository.get_current_memo(company_id)
            prior_active_claims = repository.list_claim_cards(company_id, active_only=True)
            run = RunRecord(
                company_id=company_id,
                run_kind=run_kind,
                status=RunStatus.RUNNING,
                triggered_by=triggered_by,
            )
            run.metadata = {
                **run.metadata,
                "panel_ids": selected_panels,
                "panel_policy": coverage.panel_policy,
                "schedule_policy_id": coverage.schedule_policy_id,
                "schedule_enabled": coverage.schedule_enabled,
                "preferred_run_time": coverage.preferred_run_time,
                "memo_reconciliation": policy.memo_reconciliation,
                "monitoring_enabled": policy.monitoring_enabled,
                "baseline_memo": (
                    prior_memo.model_dump(mode="json") if prior_memo is not None else None
                ),
                "baseline_active_claims": [
                    claim.model_dump(mode="json") for claim in prior_active_claims
                ],
                "baseline_active_verdicts": [
                    verdict.model_dump(mode="json")
                    for verdict in repository.list_panel_verdicts(company_id, active_only=True)
                ],
                "panel_support_assessments": [],
                "skipped_panels": [],
                "job_id": job_id,
            }
            repository.save_run(run)
        return self._execute_run(run_id=run.run_id)

    def _execute_run(
        self,
        *,
        run_id: str,
        resume_action: RunContinueAction | None = None,
    ) -> dict[str, Any]:
        error: Exception | None = None
        result: dict[str, Any] | None = None
        with self.context.database.session() as session:
            repository = Repository(session)
            run = repository.get_run(run_id)
            if run is None:
                raise KeyError(run_id)
            coverage = repository.get_coverage(run.company_id)
            if coverage is None:
                raise KeyError(f"No coverage entry for {run.company_id}")
            company_profile = repository.get_company_profile(run.company_id)
            if company_profile is None:
                raise KeyError(f"No company profile for {run.company_id}")
            runtime = RefreshRuntime.create(
                context=self.context,
                repository=repository,
                run=run,
                coverage=coverage,
                company_profile=company_profile,
            )
            selected_panels = self._panel_ids_for_run(run)
            memo_reconciliation = bool(run.metadata.get("memo_reconciliation", True))
            monitoring_enabled = bool(run.metadata.get("monitoring_enabled", True))

        from ai_investing.graphs.checkpointing import (
            checkpoint_config,
            graph_checkpointer,
            interrupt_payloads,
        )
        from ai_investing.graphs.company_refresh import build_company_refresh_graph

        try:
            with graph_checkpointer(self.context.settings) as checkpointer:
                graph = build_company_refresh_graph(
                    runtime=runtime,
                    panel_ids=selected_panels,
                    memo_reconciliation=memo_reconciliation,
                    monitoring_enabled=monitoring_enabled,
                    checkpointer=checkpointer,
                )
                config = checkpoint_config(runtime.run.run_id)
                if resume_action is None:
                    graph_result = graph.invoke(
                        {
                            "company_id": runtime.company_profile.company_id,
                            "run_id": runtime.run.run_id,
                            "panel_ids": selected_panels,
                        },
                        config=config,
                    )
                else:
                    from langgraph.types import Command

                    graph_result = graph.invoke(
                        Command(resume={"action": resume_action.value}),
                        config=config,
                    )
        except Exception as exc:
            runtime.run.status = RunStatus.FAILED
            runtime.run.completed_at = utc_now()
            runtime.run.metadata = {**runtime.run.metadata, "error": str(exc)}
            with self.context.database.session() as session:
                Repository(session).save_run(runtime.run)
            error = exc
        else:
            if interrupt_payloads(graph_result):
                runtime.run.status = RunStatus.AWAITING_CONTINUE
                runtime.run.completed_at = None
            else:
                runtime.run.status = self._terminal_status(runtime.run)
                runtime.run.completed_at = utc_now()
                with self.context.database.session() as session:
                    repository = Repository(session)
                    repository.save_run(runtime.run)
                    if self._should_advance_coverage(runtime.run):
                        runtime.coverage.last_run_at = runtime.run.completed_at
                        if runtime.run.completed_at is not None:
                            runtime.coverage.next_run_at = compute_next_run_at(
                                self.context.registries.cadence_policies,
                                runtime.coverage,
                                completed_at=runtime.run.completed_at,
                            )
                        repository.upsert_coverage(runtime.coverage)
            result = self._build_graph_result(runtime.run, graph_result)

        self._sync_operational_state(runtime=runtime, error=error)

        if error is not None:
            raise error
        assert result is not None
        return result

    def _sync_operational_state(
        self,
        *,
        runtime: RefreshRuntime,
        error: Exception | None,
    ) -> None:
        job_id = runtime.run.metadata.get("job_id")
        job_id = str(job_id) if isinstance(job_id, str) and job_id else None

        if error is not None:
            if job_id is not None:
                with self.context.database.session() as session:
                    Repository(session).fail_refresh_job(
                        job_id,
                        error_message=str(error),
                        run_id=runtime.run.run_id,
                    )
            NotificationService(self.context).emit_worker_failed(
                company_id=runtime.company_profile.company_id,
                company_name=runtime.company_profile.company_name,
                coverage_status=runtime.coverage.coverage_status,
                run_id=runtime.run.run_id,
                job_id=job_id,
                summary=str(error),
            )
            return

        if (
            runtime.run.status == RunStatus.AWAITING_CONTINUE
            and runtime.run.gate_decision == GateDecision.FAIL
        ):
            review_entry = self._ensure_review_queue_entry(runtime=runtime, job_id=job_id)
            if job_id is not None:
                with self.context.database.session() as session:
                    Repository(session).mark_refresh_job_review_required(
                        job_id,
                        run_id=runtime.run.run_id,
                        review_entry_id=review_entry.review_id,
                    )
            return

        if job_id is not None:
            with self.context.database.session() as session:
                repository = Repository(session)
                if runtime.run.status in {RunStatus.COMPLETE, RunStatus.PROVISIONAL}:
                    repository.complete_refresh_job(job_id, run_id=runtime.run.run_id)
                elif runtime.run.status in {RunStatus.GATED_OUT, RunStatus.STOPPED}:
                    review_entries = [
                        entry
                        for entry in repository.list_review_queue()
                        if entry.run_id == runtime.run.run_id
                    ]
                    if review_entries:
                        repository.mark_refresh_job_review_required(
                            job_id,
                            run_id=runtime.run.run_id,
                            review_entry_id=review_entries[0].review_id,
                        )

        if runtime.run.status in {RunStatus.COMPLETE, RunStatus.PROVISIONAL}:
            self._emit_success_notifications(runtime=runtime, job_id=job_id)

    def _ensure_review_queue_entry(
        self,
        *,
        runtime: RefreshRuntime,
        job_id: str | None,
    ) -> ReviewQueueEntry:
        with self.context.database.session() as session:
            repository = Repository(session)
            existing = next(
                (
                    entry
                    for entry in repository.list_review_queue()
                    if entry.run_id == runtime.run.run_id
                ),
                None,
            )
            if existing is not None:
                return existing
            review_entry = repository.save_review_queue_entry(
                ReviewQueueEntry(
                    company_id=runtime.company_profile.company_id,
                    company_name=runtime.company_profile.company_name,
                    coverage_status=runtime.coverage.coverage_status,
                    run_id=runtime.run.run_id,
                    job_id=job_id,
                    reason_summary=(
                        "Gatekeepers failed. Operator review is required before any "
                        "provisional continuation."
                    ),
                )
            )

        event = NotificationService(self.context).emit_gatekeeper_failed(
            company_id=runtime.company_profile.company_id,
            company_name=runtime.company_profile.company_name,
            coverage_status=runtime.coverage.coverage_status,
            run_id=runtime.run.run_id,
            review_id=review_entry.review_id,
            job_id=job_id,
            summary=review_entry.reason_summary,
        )
        review_entry.notification_event_id = event.event_id
        with self.context.database.session() as session:
            repository = Repository(session)
            repository.save_review_queue_entry(review_entry)
        return review_entry

    def _emit_success_notifications(
        self,
        *,
        runtime: RefreshRuntime,
        job_id: str | None,
    ) -> None:
        service = NotificationService(self.context)
        delta = runtime.current_delta
        if delta is not None and self._is_material_notification(delta):
            service.emit_material_change(
                company_id=runtime.company_profile.company_id,
                company_name=runtime.company_profile.company_name,
                coverage_status=runtime.coverage.coverage_status,
                run_id=runtime.run.run_id,
                job_id=job_id,
                delta=delta,
            )
        service.emit_daily_digest_candidate(
            company_id=runtime.company_profile.company_id,
            company_name=runtime.company_profile.company_name,
            coverage_status=runtime.coverage.coverage_status,
            run_id=runtime.run.run_id,
            job_id=job_id,
            delta=delta,
        )

    @staticmethod
    def _is_material_notification(delta: MonitoringDelta) -> bool:
        return bool(
            delta.changed_claim_ids
            or delta.changed_sections
            or delta.alert_level in {AlertLevel.MEDIUM, AlertLevel.HIGH}
        )

    def _resolve_panel_ids(
        self,
        *,
        coverage: CoverageEntry,
        panel_ids: list[str] | None,
        run_kind: RunKind,
    ) -> list[str]:
        policy = self.context.registries.run_policies.run_policies[coverage.panel_policy]
        requested_panel_ids = panel_ids or list(policy.default_panel_ids)
        deduped_panel_ids = list(dict.fromkeys(requested_panel_ids))
        validated_panel_ids: list[str] = []

        for panel_id in deduped_panel_ids:
            panel = self.context.get_panel(panel_id)
            if not panel.enabled:
                raise ValueError(f"Panel {panel_id} is disabled and cannot be executed.")
            if not panel.implemented and not policy.allow_unimplemented_panels:
                raise ValueError(
                    f"Panel {panel_id} is not implemented for policy {coverage.panel_policy}."
                )
            validated_panel_ids.append(panel_id)
        if validated_panel_ids and validated_panel_ids[0] != "gatekeepers":
            raise ValueError(
                "Runs must begin at gatekeepers. "
                "Resume an existing paused run for downstream panels."
            )
        if run_kind == RunKind.PANEL and validated_panel_ids != ["gatekeepers"]:
            raise ValueError(
                "run_panel can only start at gatekeepers. Use continue_run for downstream panels."
            )
        return validated_panel_ids

    def _panel_ids_for_run(self, run: RunRecord) -> list[str]:
        panel_ids = run.metadata.get("panel_ids")
        if not isinstance(panel_ids, list):
            raise ValueError(f"Run {run.run_id} is missing persisted panel_ids.")
        return [str(panel_id) for panel_id in panel_ids]

    def _build_graph_result(self, run: RunRecord, graph_result: dict[str, Any]) -> dict[str, Any]:
        panels = dict(graph_result.get("panel_results", {}))
        for panel_id, skip in RefreshRuntime._skipped_panels_from_run(run).items():
            panels.setdefault(
                panel_id,
                PanelRunRead(skip=skip).model_dump(mode="json"),
            )
        return {
            "run": run.model_dump(mode="json"),
            "panels": panels,
            "memo": graph_result.get("memo"),
            "delta": graph_result.get("delta"),
        }

    def _build_persisted_result(self, repository: Repository, run: RunRecord) -> dict[str, Any]:
        claims_by_panel: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for claim in repository.list_claim_cards(run.company_id, run_id=run.run_id):
            claims_by_panel[claim.panel_id].append(claim.model_dump(mode="json"))
        panels: dict[str, dict[str, Any]] = {
            panel_id: PanelRunRead(skip=skip).model_dump(mode="json")
            for panel_id, skip in RefreshRuntime._skipped_panels_from_run(run).items()
        }
        for verdict in repository.list_panel_verdicts(run.company_id, run_id=run.run_id):
            panels[verdict.panel_id] = PanelRunRead(
                claims=[
                    ClaimCard.model_validate(claim)
                    for claim in claims_by_panel.get(verdict.panel_id, [])
                ],
                verdict=verdict,
            ).model_dump(mode="json")
        memo = repository.get_memo_for_run(run.company_id, run.run_id)
        delta = repository.get_latest_monitoring_delta(run.company_id, run_id=run.run_id)
        return {
            "run": run.model_dump(mode="json"),
            "panels": panels,
            "memo": memo.model_dump(mode="json") if memo is not None else None,
            "delta": delta.model_dump(mode="json") if delta is not None else None,
        }

    @staticmethod
    def _terminal_status(run: RunRecord) -> RunStatus:
        if run.provisional:
            return RunStatus.PROVISIONAL
        if run.gated_out:
            return RunStatus.GATED_OUT
        if run.stopped_after_panel is not None:
            return RunStatus.STOPPED
        return RunStatus.COMPLETE

    @staticmethod
    def _should_advance_coverage(run: RunRecord) -> bool:
        return run.status in {RunStatus.COMPLETE, RunStatus.PROVISIONAL}


def render_memo_markdown(memo: ICMemo) -> str:
    lines = [f"# IC Memo: {memo.company_id}", ""]
    for section in memo.sections:
        lines.append(f"## {section.label}")
        lines.append(section.content)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_delta_json(delta: MonitoringDelta) -> str:
    return json.dumps(delta.model_dump(mode="json"), indent=2)
