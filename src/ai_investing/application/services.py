from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from ai_investing.application.context import AppContext
from ai_investing.config.models import AgentConfig, PanelConfig
from ai_investing.domain.enums import (
    AlertLevel,
    Cadence,
    CompanyType,
    GateDecision,
    MemoSectionStatus,
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
    PanelVerdict,
    RunCheckpoint,
    RunRecord,
    StructuredGenerationRequest,
    new_id,
    utc_now,
)
from ai_investing.ingestion.file_connectors import FileBundleConnector
from ai_investing.persistence.repositories import Repository

_MISSING_BASELINE = object()


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

    def ingest_public_data(self, input_dir: Path) -> tuple[CompanyProfile, list[str]]:
        return self._ingest(company_type=CompanyType.PUBLIC, input_dir=input_dir)

    def ingest_private_data(self, input_dir: Path) -> tuple[CompanyProfile, list[str]]:
        return self._ingest(company_type=CompanyType.PRIVATE, input_dir=input_dir)

    def _ingest(
        self, *, company_type: CompanyType, input_dir: Path
    ) -> tuple[CompanyProfile, list[str]]:
        connector_id = (
            "public_file_connector"
            if company_type == CompanyType.PUBLIC
            else "private_file_connector"
        )
        connector_config = next(
            connector
            for connector in self.context.registries.source_connectors.connectors
            if connector.id == connector_id
        )
        if connector_config.kind != "file_bundle":
            raise ValueError(
                f"Unsupported connector kind for {connector_id}: {connector_config.kind}"
            )
        connector = FileBundleConnector(
            manifest_file=connector_config.manifest_file,
            raw_landing_zone=Path(connector_config.raw_landing_zone),
        )
        profile, records = connector.ingest(input_dir)
        if profile.company_type != company_type:
            raise ValueError(
                f"Connector {connector_id} loaded "
                f"{profile.company_type.value} data for a "
                f"{company_type.value} workflow."
            )
        with self.context.database.session() as session:
            repository = Repository(session)
            repository.save_company_profile(profile)
            repository.save_evidence_records(records)
        return profile, [record.evidence_id for record in records]


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
            specialist_claims = self._run_specialists(
                repository=repository,
                panel=panel,
                evidence=evidence,
            )
            verdict = self._run_judge(
                repository=repository,
                panel=panel,
                claims=specialist_claims,
            )
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
        thresholds = self._delta_thresholds()
        confidence_materiality = float(thresholds.get("confidence_materiality", 0.05))
        always_refresh_sections = self._threshold_string_set("always_refresh_sections")
        if not always_refresh_sections:
            always_refresh_sections = {"what_changed_since_last_run"}
        high_alert_sections = self._threshold_string_set("high_alert_changed_sections")
        medium_alert_sections = self._threshold_string_set("medium_alert_changed_sections")
        high_alert_drift_flags = self._threshold_string_set("high_alert_drift_flags")
        medium_alert_claim_change_count = int(
            thresholds.get(
                "medium_alert_claim_change_count",
                thresholds.get("claim_change_count_for_alert", 1),
            )
        )
        prior_claim_map = {
            (claim.factor_id, claim.agent_id): claim for claim in self.prior_active_claims
        }
        changed_claim_ids: list[str] = []
        drift_flags: set[str] = set()
        materially_impacted_sections: set[str] = set()
        for claim in self.current_claims:
            prior_claim = prior_claim_map.get((claim.factor_id, claim.agent_id))
            if not self._claim_change_is_material(
                prior_claim=prior_claim,
                claim=claim,
                confidence_materiality=confidence_materiality,
            ):
                continue
            changed_claim_ids.append(claim.claim_id)
            materially_impacted_sections.update(
                impact.section_id for impact in claim.section_impacts
            )
            drift_flags.update(self._drift_flags_for_claim_change(claim))

        gate_decision_changed = self._gatekeeper_decision_changed()
        materially_impacted_sections.update(self._verdict_changed_sections())
        material_sections = [
            section_id
            for section_id, section in self.current_sections.items()
            if section_id not in always_refresh_sections
            if self._section_change_is_material(
                section_id=section_id,
                section=section,
                materially_impacted_sections=materially_impacted_sections,
            )
        ]

        if self.prior_memo is None:
            summary = "Initial coverage run. No prior memo exists."
        else:
            summary = self._monitoring_change_summary(
                changed_claim_ids=changed_claim_ids,
                changed_sections=material_sections,
                drift_flags=drift_flags,
                gate_decision_changed=gate_decision_changed,
            )
        delta = MonitoringDelta(
            company_id=self.company_profile.company_id,
            prior_run_id=self.prior_memo.run_id if self.prior_memo is not None else None,
            current_run_id=self.run.run_id,
            changed_claim_ids=changed_claim_ids,
            changed_sections=material_sections,
            change_summary=summary,
            thesis_drift_flags=sorted(drift_flags),
            alert_level=self._delta_alert_level(
                changed_claim_ids=changed_claim_ids,
                changed_sections=material_sections,
                drift_flags=drift_flags,
                gate_decision_changed=gate_decision_changed,
                high_alert_sections=high_alert_sections,
                medium_alert_sections=medium_alert_sections,
                high_alert_drift_flags=high_alert_drift_flags,
                medium_alert_claim_change_count=medium_alert_claim_change_count,
            ),
        )
        self._update_delta_section(delta)
        delta.changed_sections = sorted(
            set(delta.changed_sections).union(
                section_id
                for section_id in always_refresh_sections
                if section_id in self.current_sections
            )
        )
        self.current_delta = delta
        with self.context.database.session() as session:
            Repository(session).save_monitoring_delta(delta)
        return delta

    def skip_monitoring_delta(self) -> MonitoringDelta:
        delta = MonitoringDelta(
            company_id=self.company_profile.company_id,
            prior_run_id=self.prior_memo.run_id if self.prior_memo is not None else None,
            current_run_id=self.run.run_id,
            change_summary="Monitoring disabled by run policy.",
            alert_level=AlertLevel.LOW,
        )
        self._update_delta_section(delta)
        delta.changed_sections = ["what_changed_since_last_run"]
        self.current_delta = delta
        with self.context.database.session() as session:
            Repository(session).save_monitoring_delta(delta)
        return delta

    def reconcile_ic_memo(self) -> ICMemo:
        memo = self._build_memo(is_partial=False)
        with self.context.database.session() as session:
            Repository(session).save_memo(memo)
        return memo

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
                            "namespace": (
                                f"company/{self.company_profile.company_id}/"
                                f"claims/{factor_id}"
                            ),
                        },
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
        repository.save_panel_verdict(verdict)
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
        summary_prefix = "Gatekeeper lead:" if panel.id == "gatekeepers" else "Panel lead:"
        updated = verdict.model_copy(
            update={
                "verdict_id": new_id("vrd"),
                "summary": f"{summary_prefix} {verdict.summary}",
                "supersedes_verdict_id": verdict.verdict_id,
            }
        )
        with self.context.database.session() as session:
            Repository(session).save_panel_verdict(updated)
        self.current_verdicts[panel_id] = updated
        return updated

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
            return "Gatekeepers passed. Continue explicitly to run downstream panels."
        return "Gatekeepers passed. Finalize by stopping after this panel."


@dataclass
class AnalysisService:
    context: AppContext

    def initialize_database(self) -> None:
        self.context.database.initialize()

    def analyze_company(
        self, company_id: str, panel_ids: list[str] | None = None
    ) -> dict[str, Any]:
        return self._start_run(
            company_id=company_id,
            panel_ids=panel_ids,
            run_kind=RunKind.ANALYZE,
        )

    def refresh_company(self, company_id: str) -> dict[str, Any]:
        return self._start_run(
            company_id=company_id,
            panel_ids=None,
            run_kind=RunKind.REFRESH,
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
            run = RunRecord(company_id=company_id, run_kind=run_kind, status=RunStatus.RUNNING)
            run.metadata = {
                **run.metadata,
                "panel_ids": selected_panels,
                "panel_policy": coverage.panel_policy,
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
                        if (
                            runtime.coverage.cadence == Cadence.WEEKLY
                            and runtime.run.completed_at is not None
                        ):
                            runtime.coverage.next_run_at = (
                                runtime.run.completed_at + timedelta(days=7)
                            )
                        repository.upsert_coverage(runtime.coverage)
            result = self._build_graph_result(runtime.run, graph_result)

        if error is not None:
            raise error
        assert result is not None
        return result

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
        return {
            "run": run.model_dump(mode="json"),
            "panels": graph_result.get("panel_results", {}),
            "memo": graph_result.get("memo"),
            "delta": graph_result.get("delta"),
        }

    def _build_persisted_result(self, repository: Repository, run: RunRecord) -> dict[str, Any]:
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
        return run.status in {
            RunStatus.COMPLETE,
            RunStatus.PROVISIONAL,
            RunStatus.GATED_OUT,
            RunStatus.STOPPED,
        }


def render_memo_markdown(memo: ICMemo) -> str:
    lines = [f"# IC Memo: {memo.company_id}", ""]
    for section in memo.sections:
        lines.append(f"## {section.label}")
        lines.append(section.content)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_delta_json(delta: MonitoringDelta) -> str:
    return json.dumps(delta.model_dump(mode="json"), indent=2)
