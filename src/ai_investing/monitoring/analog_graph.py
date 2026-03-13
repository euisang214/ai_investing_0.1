from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_investing.domain.models import CompanyProfile, EvidenceRecord, MonitoringReference, SourceRef
from ai_investing.persistence.repositories import Repository


@dataclass(frozen=True, slots=True)
class _FactorSnapshot:
    factor_id: str
    stance: str
    summary: str
    metrics: dict[str, Any]
    source_ref: SourceRef | None


@dataclass(frozen=True, slots=True)
class _CompanySnapshot:
    profile: CompanyProfile
    factors: dict[str, _FactorSnapshot]


class AnalogGraph:
    def __init__(
        self,
        *,
        max_references: int = 2,
        min_score: float = 1.0,
        factor_overlap_weight: float = 1.0,
        stance_match_weight: float = 0.6,
        metric_overlap_weight: float = 0.25,
    ) -> None:
        self.max_references = max_references
        self.min_score = min_score
        self.factor_overlap_weight = factor_overlap_weight
        self.stance_match_weight = stance_match_weight
        self.metric_overlap_weight = metric_overlap_weight

    @classmethod
    def from_mapping(cls, config: dict[str, Any] | None) -> AnalogGraph:
        config = config or {}
        return cls(
            max_references=int(config.get("max_references", 2)),
            min_score=float(config.get("min_score", 1.0)),
            factor_overlap_weight=float(config.get("factor_overlap_weight", 1.0)),
            stance_match_weight=float(config.get("stance_match_weight", 0.6)),
            metric_overlap_weight=float(config.get("metric_overlap_weight", 0.25)),
        )

    def rank_company(
        self,
        repository: Repository,
        company_id: str,
        *,
        factor_ids: list[str] | None = None,
        limit: int | None = None,
    ) -> list[MonitoringReference]:
        target_profile = repository.get_company_profile(company_id)
        if target_profile is None:
            return []
        target_snapshot = self._snapshot_company(
            target_profile,
            repository.list_evidence(company_id),
        )
        if not target_snapshot.factors:
            return []

        requested_factor_ids = set(factor_ids or target_snapshot.factors)
        references: list[MonitoringReference] = []
        for coverage in repository.list_coverage():
            if coverage.company_id == company_id:
                continue
            candidate_profile = repository.get_company_profile(coverage.company_id)
            if candidate_profile is None:
                continue
            candidate_snapshot = self._snapshot_company(
                candidate_profile,
                repository.list_evidence(coverage.company_id),
            )
            if not candidate_snapshot.factors:
                continue
            reference = self._score_candidate(
                target_snapshot=target_snapshot,
                candidate_snapshot=candidate_snapshot,
                factor_ids=requested_factor_ids,
            )
            if reference is not None:
                references.append(reference)

        references.sort(
            key=lambda reference: (
                -(reference.score or 0.0),
                reference.company_id or "",
                reference.factor_id or "",
                reference.label,
            )
        )
        result_limit = limit or self.max_references
        return references[: max(0, result_limit)]

    def _score_candidate(
        self,
        *,
        target_snapshot: _CompanySnapshot,
        candidate_snapshot: _CompanySnapshot,
        factor_ids: set[str],
    ) -> MonitoringReference | None:
        overlap = sorted(
            factor_id
            for factor_id in factor_ids
            if factor_id in target_snapshot.factors and factor_id in candidate_snapshot.factors
        )
        if not overlap:
            return None

        score = 0.0
        rationale_bits: list[str] = []
        top_factor_id = overlap[0]
        top_factor_score = -1.0
        for factor_id in overlap:
            target_factor = target_snapshot.factors[factor_id]
            candidate_factor = candidate_snapshot.factors[factor_id]
            factor_score = self.factor_overlap_weight
            shared_metric_keys = set(target_factor.metrics).intersection(candidate_factor.metrics)
            if target_factor.stance == candidate_factor.stance:
                factor_score += self.stance_match_weight
            if shared_metric_keys:
                factor_score += self.metric_overlap_weight * min(2, len(shared_metric_keys))
            score += factor_score
            if factor_score > top_factor_score:
                top_factor_id = factor_id
                top_factor_score = factor_score
            shared_shape = "shares the same stance"
            if target_factor.stance != candidate_factor.stance:
                shared_shape = "shows a related but not identical stance"
            rationale_bits.append(
                f"{factor_id.replace('_', ' ')} {shared_shape}"
            )

        if score < self.min_score:
            return None

        top_factor = candidate_snapshot.factors[top_factor_id]
        category = (
            "analog"
            if candidate_snapshot.profile.company_type == target_snapshot.profile.company_type
            else "base_rate"
        )
        shared = ", ".join(rationale_bits[:2])
        return MonitoringReference(
            category=category,
            label=candidate_snapshot.profile.company_name,
            rationale=(
                f"{candidate_snapshot.profile.company_name} ranks as a {category.replace('_', ' ')} "
                f"because {shared}."
            ),
            factor_id=top_factor_id,
            company_id=candidate_snapshot.profile.company_id,
            company_name=candidate_snapshot.profile.company_name,
            source_ref=top_factor.source_ref,
            score=round(score, 2),
        )

    @staticmethod
    def _snapshot_company(
        profile: CompanyProfile,
        evidence_records: list[EvidenceRecord],
    ) -> _CompanySnapshot:
        latest_by_factor: dict[str, _FactorSnapshot] = {}
        ordered_records = sorted(
            evidence_records,
            key=lambda record: (
                record.as_of_date,
                record.created_at,
                record.evidence_id,
            ),
            reverse=True,
        )
        for record in ordered_records:
            source_ref = record.source_refs[0] if record.source_refs else SourceRef(label=record.title)
            for factor_id, signal in record.factor_signals.items():
                if factor_id in latest_by_factor:
                    continue
                latest_by_factor[factor_id] = _FactorSnapshot(
                    factor_id=factor_id,
                    stance=signal.stance,
                    summary=signal.summary,
                    metrics=dict(signal.metrics),
                    source_ref=source_ref,
                )
        return _CompanySnapshot(profile=profile, factors=latest_by_factor)
