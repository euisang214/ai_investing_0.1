from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ai_investing.config.models import (
    MonitoringConcentrationView,
    MonitoringConfig,
    MonitoringDriftRule,
)
from ai_investing.domain.enums import AlertLevel
from ai_investing.domain.models import (
    ClaimCard,
    CompanyProfile,
    EvidenceRecord,
    GatekeeperVerdict,
    ICMemo,
    MemoSection,
    MonitoringCurrentState,
    MonitoringDelta,
    MonitoringReason,
    MonitoringReference,
    PanelVerdict,
    RunRecord,
)
from ai_investing.monitoring.analog_graph import AnalogGraph
from ai_investing.persistence.repositories import Repository


class ClaimContradictionService:
    def __init__(
        self,
        *,
        positive_markers: list[str] | None = None,
        negative_markers: list[str] | None = None,
        minimum_confidence: float = 0.45,
        max_references: int = 2,
    ) -> None:
        self.positive_markers = tuple(
            marker.lower() for marker in (positive_markers or [])
        )
        self.negative_markers = tuple(
            marker.lower() for marker in (negative_markers or [])
        )
        self.minimum_confidence = minimum_confidence
        self.max_references = max_references

    @classmethod
    def from_mapping(cls, config: dict[str, Any] | None) -> ClaimContradictionService:
        config = config or {}
        return cls(
            positive_markers=list(config.get("positive_markers", [])),
            negative_markers=list(config.get("negative_markers", [])),
            minimum_confidence=float(config.get("minimum_confidence", 0.45)),
            max_references=int(config.get("max_references", 2)),
        )

    def find_references(
        self,
        *,
        claims: list[ClaimCard],
        evidence_records: list[EvidenceRecord],
        factor_ids: list[str] | None = None,
    ) -> list[MonitoringReference]:
        requested_factor_ids = set(factor_ids or [])
        contradictions: list[MonitoringReference] = []
        evidence_by_factor: dict[str, list[EvidenceRecord]] = defaultdict(list)
        for record in evidence_records:
            for factor_id in record.factor_signals:
                if requested_factor_ids and factor_id not in requested_factor_ids:
                    continue
                evidence_by_factor[factor_id].append(record)

        claims_by_factor: dict[str, list[ClaimCard]] = defaultdict(list)
        for claim in claims:
            if requested_factor_ids and claim.factor_id not in requested_factor_ids:
                continue
            claims_by_factor[claim.factor_id].append(claim)

        factor_pool = sorted(set(evidence_by_factor).union(claims_by_factor))
        for factor_id in factor_pool:
            evidence_stances = self._evidence_stances(
                evidence_by_factor.get(factor_id, []),
                factor_id,
            )
            claim_stances = self._claim_stances(claims_by_factor.get(factor_id, []))
            contradiction_stances = evidence_stances
            if contradiction_stances:
                if not self._is_meaningfully_contradictory(contradiction_stances):
                    continue
            else:
                contradiction_stances = claim_stances
                if not self._is_meaningfully_contradictory(contradiction_stances):
                    continue
            if not contradiction_stances:
                continue
            recent_record = self._latest_record(evidence_by_factor.get(factor_id, []))
            label = factor_id.replace("_", " ")
            contradictions.append(
                MonitoringReference(
                    category="contradiction",
                    label=label,
                    rationale=(
                        f"Conflicting evidence persists on {label}: "
                        f"signals span {', '.join(sorted(contradiction_stances))}."
                    ),
                    factor_id=factor_id,
                    source_ref=(
                        recent_record.source_refs[0]
                        if recent_record is not None and recent_record.source_refs
                        else None
                    ),
                )
            )

        contradictions.sort(key=lambda reference: (reference.factor_id or "", reference.label))
        return contradictions[: self.max_references]

    def _claim_stances(self, claims: list[ClaimCard]) -> set[str]:
        stances: set[str] = set()
        for claim in claims:
            if claim.confidence < self.minimum_confidence:
                continue
            text = " ".join((claim.claim, claim.bull_case, claim.bear_case)).lower()
            if any(marker in text for marker in self.positive_markers):
                stances.add("positive")
            if any(marker in text for marker in self.negative_markers):
                stances.add("negative")
        return stances

    @staticmethod
    def _evidence_stances(records: list[EvidenceRecord], factor_id: str) -> set[str]:
        stances: set[str] = set()
        for record in records:
            signal = record.factor_signals.get(factor_id)
            if signal is None:
                continue
            stances.add(signal.stance)
        return stances

    @staticmethod
    def _is_meaningfully_contradictory(stances: set[str]) -> bool:
        if "positive" in stances and "negative" in stances:
            return True
        return "mixed" in stances and bool({"positive", "negative"}.intersection(stances))

    @staticmethod
    def _latest_record(records: list[EvidenceRecord]) -> EvidenceRecord | None:
        if not records:
            return None
        return max(
            records,
            key=lambda record: (
                record.as_of_date,
                record.created_at,
                record.evidence_id,
            ),
        )


@dataclass(slots=True)
class MonitoringDeltaService:
    config: MonitoringConfig
    company_profile: CompanyProfile
    run: RunRecord
    prior_memo: ICMemo | None
    current_sections: dict[str, MemoSection]
    prior_active_claims: list[ClaimCard]
    current_claims: list[ClaimCard]
    prior_active_verdicts: dict[str, PanelVerdict]
    current_verdicts: dict[str, PanelVerdict]
    current_evidence: list[EvidenceRecord]
    analog_references: list[MonitoringReference]

    @classmethod
    def from_runtime(cls, runtime: Any) -> MonitoringDeltaService:
        config = runtime.context.registries.monitoring.monitoring
        with runtime.context.database.session() as session:
            repository = Repository(session)
            current_evidence = repository.list_evidence(runtime.company_profile.company_id)
            analog_graph = AnalogGraph.from_mapping(
                config.analog.model_dump(mode="python")
            )
            analog_references = analog_graph.rank_company(
                repository,
                runtime.company_profile.company_id,
                factor_ids=sorted({claim.factor_id for claim in runtime.current_claims}),
            )
        return cls(
            config=config,
            company_profile=runtime.company_profile,
            run=runtime.run,
            prior_memo=runtime.prior_memo,
            current_sections=runtime.current_sections,
            prior_active_claims=runtime.prior_active_claims,
            current_claims=runtime.current_claims,
            prior_active_verdicts=runtime.prior_active_verdicts,
            current_verdicts=runtime.current_verdicts,
            current_evidence=current_evidence,
            analog_references=analog_references,
        )

    def compute_delta(self) -> MonitoringDelta:
        thresholds = dict(self.config.delta_thresholds)
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
        changed_claims: list[ClaimCard] = []
        changed_claim_ids: list[str] = []
        drift_flags: set[str] = set()
        trigger_reasons: list[MonitoringReason] = []
        materially_impacted_sections: set[str] = set()

        for claim in self.current_claims:
            prior_claim = prior_claim_map.get((claim.factor_id, claim.agent_id))
            if not self._claim_change_is_material(
                prior_claim=prior_claim,
                claim=claim,
                confidence_materiality=confidence_materiality,
            ):
                continue
            changed_claims.append(claim)
            changed_claim_ids.append(claim.claim_id)
            materially_impacted_sections.update(
                impact.section_id for impact in claim.section_impacts
            )
            rule_flags, rule_reasons = self._drift_rules_for_claim(claim)
            drift_flags.update(rule_flags)
            trigger_reasons.extend(rule_reasons)

        gate_decision_changed = self._gatekeeper_decision_changed()
        panel_change_hints = self._panel_change_hints(confidence_materiality)
        trigger_reasons.extend(panel_change_hints)
        materially_impacted_sections.update(self._verdict_changed_sections())

        contradictions = self._contradictions()
        for contradiction in contradictions:
            trigger_reasons.append(
                MonitoringReason(
                    category="contradiction",
                    summary=contradiction.rationale,
                    factor_id=contradiction.factor_id,
                    severity="medium",
                    related_section_ids=self._section_ids_for_factor(contradiction.factor_id),
                )
            )

        concentration_signals = self._concentration_signals()
        for signal in concentration_signals:
            if signal.state == "stable":
                continue
            trigger_reasons.append(
                MonitoringReason(
                    category="concentration",
                    summary=signal.summary,
                    factor_id=signal.factor_id,
                    severity="medium",
                    related_section_ids=self._section_ids_for_factor(signal.factor_id),
                )
            )

        if self.analog_references:
            top_analog = self.analog_references[0]
            trigger_reasons.append(
                MonitoringReason(
                    category=top_analog.category,
                    summary=top_analog.rationale,
                    factor_id=top_analog.factor_id,
                    severity="info",
                    related_section_ids=self._section_ids_for_factor(top_analog.factor_id),
                )
            )

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

        change_summary = self._monitoring_change_summary(
            changed_claim_ids=changed_claim_ids,
            changed_sections=material_sections,
            drift_flags=drift_flags,
            gate_decision_changed=gate_decision_changed,
            contradictions=contradictions,
            analog_references=self.analog_references,
        )
        delta = MonitoringDelta(
            company_id=self.company_profile.company_id,
            prior_run_id=self.prior_memo.run_id if self.prior_memo is not None else None,
            current_run_id=self.run.run_id,
            changed_claim_ids=changed_claim_ids,
            changed_sections=material_sections,
            change_summary=change_summary,
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
            trigger_reasons=self._dedupe_reasons(trigger_reasons),
            contradiction_references=contradictions,
            analog_references=self.analog_references,
            concentration_signals=concentration_signals,
            panel_change_hints=panel_change_hints,
        )
        delta.changed_sections = sorted(
            set(delta.changed_sections).union(
                section_id
                for section_id in always_refresh_sections
                if section_id in self.current_sections
            )
        )
        return delta

    def build_disabled_delta(self) -> MonitoringDelta:
        return MonitoringDelta(
            company_id=self.company_profile.company_id,
            prior_run_id=self.prior_memo.run_id if self.prior_memo is not None else None,
            current_run_id=self.run.run_id,
            change_summary="Monitoring disabled by run policy.",
            alert_level=AlertLevel.LOW,
            changed_sections=["what_changed_since_last_run"],
            concentration_signals=self._concentration_signals(),
        )

    def _threshold_string_set(self, key: str) -> set[str]:
        value = self.config.delta_thresholds.get(key, [])
        if not isinstance(value, list):
            return set()
        return {str(item) for item in value}

    def _drift_rules_for_claim(self, claim: ClaimCard) -> tuple[set[str], list[MonitoringReason]]:
        flags: set[str] = set()
        reasons: list[MonitoringReason] = []
        for rule in self._matching_drift_rules(claim.factor_id):
            flags.add(rule.drift_flag)
            reasons.append(
                MonitoringReason(
                    category="drift",
                    summary=rule.reason,
                    factor_id=claim.factor_id,
                    severity="medium",
                    related_section_ids=rule.related_section_ids
                    or self._section_ids_for_factor(claim.factor_id),
                )
            )
        return flags, reasons

    def _matching_drift_rules(self, factor_id: str) -> list[MonitoringDriftRule]:
        return [rule for rule in self.config.drift_rules if factor_id in rule.factor_ids]

    def _concentration_signals(self) -> list[MonitoringCurrentState]:
        latest_signal_by_factor = self._latest_signal_by_factor()
        signals: list[MonitoringCurrentState] = []
        for view in self.config.concentration_views:
            current_signal = self._current_signal_for_view(view, latest_signal_by_factor)
            if current_signal is None:
                continue
            state = (
                view.pressured_state
                if current_signal["stance"] in set(view.worsening_stances)
                else view.stable_state
            )
            signals.append(
                MonitoringCurrentState(
                    category=view.id,
                    label=view.label,
                    factor_id=current_signal["factor_id"],
                    state=state,
                    summary=(
                        f"{view.label} is currently {state}: {current_signal['summary']}"
                    ),
                    metrics=current_signal["metrics"],
                )
            )
        signals.sort(key=lambda signal: (signal.category, signal.factor_id, signal.label))
        return signals

    def _latest_signal_by_factor(self) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        ordered_records = sorted(
            self.current_evidence,
            key=lambda record: (
                record.as_of_date,
                record.created_at,
                record.evidence_id,
            ),
            reverse=True,
        )
        for record in ordered_records:
            for factor_id, signal in record.factor_signals.items():
                if factor_id in latest:
                    continue
                metrics = dict(signal.metrics)
                latest[factor_id] = {
                    "factor_id": factor_id,
                    "stance": signal.stance,
                    "summary": signal.summary,
                    "metrics": metrics,
                }
        return latest

    @staticmethod
    def _current_signal_for_view(
        view: MonitoringConcentrationView,
        latest_signal_by_factor: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        for factor_id in view.factor_ids:
            signal = latest_signal_by_factor.get(factor_id)
            if signal is None:
                continue
            metrics = {
                key: value
                for key, value in signal["metrics"].items()
                if not view.metric_keys or key in set(view.metric_keys)
            }
            return {**signal, "metrics": metrics}
        return None

    def _contradictions(self) -> list[MonitoringReference]:
        service = ClaimContradictionService.from_mapping(
            self.config.contradiction.model_dump(mode="python")
        )
        return service.find_references(
            claims=self.current_claims,
            evidence_records=self.current_evidence,
            factor_ids=sorted({claim.factor_id for claim in self.current_claims}),
        )

    def _panel_change_hints(self, confidence_materiality: float) -> list[MonitoringReason]:
        hints: list[MonitoringReason] = []
        for panel_id, verdict in sorted(self.current_verdicts.items()):
            prior_verdict = self.prior_active_verdicts.get(panel_id)
            if prior_verdict is None:
                hints.append(
                    MonitoringReason(
                        category="panel_change",
                        summary=f"{panel_id} produced a new panel verdict in this run.",
                        severity="info",
                        related_section_ids=verdict.affected_section_ids,
                    )
                )
                continue
            if verdict.recommendation != prior_verdict.recommendation:
                hints.append(
                    MonitoringReason(
                        category="panel_change",
                        summary=(
                            f"{panel_id} recommendation moved from "
                            f"{prior_verdict.recommendation.value} to "
                            f"{verdict.recommendation.value}."
                        ),
                        severity="medium",
                        related_section_ids=verdict.affected_section_ids,
                    )
                )
                continue
            if abs(verdict.confidence - prior_verdict.confidence) >= confidence_materiality:
                hints.append(
                    MonitoringReason(
                        category="panel_change",
                        summary=(
                            f"{panel_id} confidence moved from {prior_verdict.confidence:.2f} "
                            f"to {verdict.confidence:.2f}."
                        ),
                        severity="info",
                        related_section_ids=verdict.affected_section_ids,
                    )
                )
        return hints

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
        contradictions: list[MonitoringReference],
        analog_references: list[MonitoringReference],
    ) -> str:
        if self.prior_memo is None:
            return "Initial coverage run. No prior memo exists."
        if (
            not changed_claim_ids
            and not changed_sections
            and not drift_flags
            and not gate_decision_changed
            and not contradictions
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
        if contradictions:
            contradiction_factors = ", ".join(
                sorted(
                    reference.factor_id or reference.label.replace(" ", "_")
                    for reference in contradictions
                )
            )
            parts.append(f"Contradictions: {contradiction_factors}.")
        if analog_references:
            parts.append(f"Top analog: {analog_references[0].label}.")
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

    def _section_ids_for_factor(self, factor_id: str | None) -> list[str]:
        if factor_id is None:
            return []
        section_ids = {
            impact.section_id
            for claim in self.current_claims
            if claim.factor_id == factor_id
            for impact in claim.section_impacts
        }
        return sorted(section_ids)

    @staticmethod
    def _dedupe_reasons(reasons: list[MonitoringReason]) -> list[MonitoringReason]:
        deduped: dict[tuple[str, str | None, str], MonitoringReason] = {}
        for reason in reasons:
            key = (reason.category, reason.factor_id, reason.summary)
            deduped[key] = reason
        return [
            deduped[key]
            for key in sorted(
                deduped,
                key=lambda item: (
                    item[0],
                    item[1] or "",
                    item[2],
                ),
            )
        ]
