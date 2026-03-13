from __future__ import annotations

from collections import Counter
from typing import Any

from ai_investing.domain.enums import (
    ChangeClassification,
    GateDecision,
    MemoSectionStatus,
    VerdictRecommendation,
)
from ai_investing.domain.models import (
    ClaimCard,
    EvidenceRecord,
    EvidenceSnippet,
    GatekeeperVerdict,
    ICMemo,
    MemoSection,
    MemoSectionUpdate,
    PanelVerdict,
    SectionImpact,
    SourceRef,
    StructuredGenerationRequest,
)
from ai_investing.providers.base import ModelProvider, ModelT

STALE_EVIDENCE_DAYS = 30


def _as_evidence(records: list[dict[str, Any]]) -> list[EvidenceRecord]:
    return [EvidenceRecord.model_validate(record) for record in records]


def _score_signals(
    evidence: list[EvidenceRecord], factor_id: str
) -> tuple[int, list[str], list[str]]:
    score = 0
    positives: list[str] = []
    negatives: list[str] = []
    for record in evidence:
        signal = record.factor_signals.get(factor_id)
        if signal is None:
            continue
        if signal.stance == "positive":
            score += 1
            positives.append(signal.summary)
        elif signal.stance == "negative":
            score -= 1
            negatives.append(signal.summary)
        else:
            positives.append(signal.summary)
            negatives.append(signal.summary)
    return score, positives, negatives


def _relevant_evidence(evidence: list[EvidenceRecord], factor_id: str) -> list[EvidenceRecord]:
    return [record for record in evidence if factor_id in record.factor_ids]


def _stale_records(evidence: list[EvidenceRecord], factor_id: str) -> list[EvidenceRecord]:
    return [
        record
        for record in _relevant_evidence(evidence, factor_id)
        if record.staleness_days >= STALE_EVIDENCE_DAYS
    ]


def _snippets(
    evidence: list[EvidenceRecord], factor_id: str, *, negative: bool
) -> list[EvidenceSnippet]:
    snippets: list[EvidenceSnippet] = []
    target = "negative" if negative else "positive"
    for record in evidence:
        signal = record.factor_signals.get(factor_id)
        if signal is None:
            continue
        if signal.stance != target and signal.stance != "mixed":
            continue
        source_ref = record.source_refs[0] if record.source_refs else SourceRef(label=record.title)
        snippets.append(EvidenceSnippet(summary=signal.summary, source_ref=source_ref))
    return snippets[:3]


class FakeModelProvider(ModelProvider):
    def generate_structured(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> ModelT:
        if response_model is ClaimCard:
            return response_model.model_validate(  # type: ignore[return-value]
                self._claim_card_payload(request)
            )
        if response_model is PanelVerdict:
            if request.task_type == "panel_lead":
                return response_model.model_validate(  # type: ignore[return-value]
                    self._panel_lead_payload(request)
                )
            return response_model.model_validate(  # type: ignore[return-value]
                self._panel_verdict_payload(request)
            )
        if response_model is GatekeeperVerdict:
            if request.task_type == "panel_lead":
                return response_model.model_validate(  # type: ignore[return-value]
                    self._panel_lead_payload(request)
                )
            return response_model.model_validate(  # type: ignore[return-value]
                self._gatekeeper_payload(request)
            )
        if response_model is MemoSectionUpdate:
            return response_model.model_validate(  # type: ignore[return-value]
                self._memo_section_update_payload(request)
            )
        if response_model is ICMemo:
            return response_model.model_validate(  # type: ignore[return-value]
                self._ic_memo_payload(request)
            )
        raise ValueError(f"Unsupported fake response model: {response_model.__name__}")

    def _claim_card_payload(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        evidence = _as_evidence(request.input_data["evidence"])
        factor_id = str(request.input_data["factor_id"])
        factor_name = str(request.input_data["factor_name"])
        agent_id = str(request.input_data["agent_id"])
        role_type = str(request.input_data["role_type"])
        score, positives, negatives = _score_signals(evidence, factor_id)
        prior_claim_text = str(request.input_data.get("prior_claim", ""))
        relevant_evidence = _relevant_evidence(evidence, factor_id)
        stale_evidence = _stale_records(evidence, factor_id)
        confidence = min(0.95, 0.45 + (abs(score) * 0.12))
        evidence_quality = (
            sum(record.evidence_quality for record in evidence if factor_id in record.factor_ids)
            or 0.6
        )
        relevant_count = max(1, len(relevant_evidence))
        evidence_quality = min(0.95, evidence_quality / relevant_count)
        if stale_evidence:
            stale_ratio = len(stale_evidence) / relevant_count
            confidence = max(0.25, confidence - min(0.18, 0.08 + (stale_ratio * 0.08)))
            evidence_quality = max(
                0.2,
                evidence_quality - min(0.15, 0.04 + (stale_ratio * 0.06)),
            )
        claim_direction = "durable" if score >= 0 else "under pressure"
        if role_type == "skeptic" and score >= 0:
            claim_direction = "more fragile than the base case implies"
        if role_type == "durability":
            claim_direction = (
                "durable through a medium-term stress case"
                if score >= 0
                else "fragile under stress"
            )

        top_positive = positives[0] if positives else f"evidence is mixed for {factor_name.lower()}"
        top_negative = (
            negatives[0]
            if negatives
            else f"few direct negatives surfaced for {factor_name.lower()}"
        )
        if stale_evidence:
            top_negative = (
                f"Part of the support is stale ({len(stale_evidence)}/{relevant_count} records "
                f"are at least {STALE_EVIDENCE_DAYS} days old)."
            )
        what_changed = (
            "Initial coverage run."
            if not prior_claim_text
            else "Signal mix changed versus the prior active claim."
        )
        if stale_evidence:
            what_changed = (
                "Stale evidence is weakening conviction versus the freshest possible read."
            )
        staleness_assessment = "Fresh enough for current memo update."
        if stale_evidence:
            staleness_assessment = (
                f"Stale evidence is carrying {len(stale_evidence)} of {relevant_count} records "
                f"(>= {STALE_EVIDENCE_DAYS} days old), so confidence is downgraded until refreshed."
            )
        return {
            "company_id": request.input_data["company_id"],
            "company_type": request.input_data["company_type"],
            "run_id": request.input_data["run_id"],
            "panel_id": request.input_data["panel_id"],
            "factor_id": factor_id,
            "agent_id": agent_id,
            "claim": (
                f"{request.input_data['company_name']} appears "
                f"{claim_direction} on {factor_name.lower()}."
            ),
            "bull_case": top_positive,
            "bear_case": top_negative,
            "evidence_for": [
                snippet.model_dump(mode="json")
                for snippet in _snippets(evidence, factor_id, negative=False)
            ],
            "evidence_against": [
                snippet.model_dump(mode="json")
                for snippet in _snippets(evidence, factor_id, negative=True)
            ],
            "confidence": round(confidence, 2),
            "evidence_quality": round(evidence_quality, 2),
            "staleness_assessment": staleness_assessment,
            "time_horizon": "12-24 months",
            "durability_horizon": "multi-year",
            "falsifiers": [f"{factor_name} weakens materially in the next refresh."],
            "what_changed": what_changed,
            "unresolved_questions": [
                f"What could invert the current {factor_name.lower()} signal?"
            ],
            "recommended_followups": [
                (
                    f"Refresh stale evidence on {factor_name.lower()} before relying on this read."
                    if stale_evidence
                    else f"Refresh evidence on {factor_name.lower()} during the next weekly rerun."
                )
            ],
            "source_refs": [
                source_ref.model_dump(mode="json")
                for record in evidence
                for source_ref in record.source_refs[:1]
                if factor_id in record.factor_ids
            ][:3],
            "section_impacts": [
                SectionImpact(
                    section_id=section_id,
                    rationale=f"{factor_name} affects {section_id.replace('_', ' ')}.",
                ).model_dump(mode="json")
                for section_id in request.input_data["section_ids"]
            ],
            "namespace": request.input_data["namespace"],
            "supersedes_claim_id": request.input_data.get("supersedes_claim_id"),
        }

    def _panel_verdict_payload(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        claims = [ClaimCard.model_validate(claim) for claim in request.input_data["claims"]]
        company_name = str(request.input_data["company_name"])
        positive = sum(
            1
            for claim in claims
            if "under pressure" not in claim.claim and "fragile" not in claim.claim
        )
        negative = len(claims) - positive
        recommendation = VerdictRecommendation.POSITIVE
        if negative > positive:
            recommendation = VerdictRecommendation.NEGATIVE
        elif negative:
            recommendation = VerdictRecommendation.MIXED
        strengths = [claim.bull_case for claim in claims[:3]]
        concerns = [claim.bear_case for claim in claims[:3]]
        stale_claims = [
            claim for claim in claims if "stale" in claim.staleness_assessment.lower()
        ]
        confidence = round(sum(claim.confidence for claim in claims) / max(1, len(claims)), 2)
        summary = (
            f"{company_name} shows a {recommendation.value} read on "
            f"{request.input_data['panel_name'].lower()}."
        )
        if stale_claims:
            confidence = round(max(0.2, confidence - 0.05), 2)
            concerns.append("Part of the evidence set is stale, which lowers conviction.")
            summary = f"{summary} Current conviction is tempered by stale evidence."
        return {
            "company_id": request.input_data["company_id"],
            "company_type": request.input_data["company_type"],
            "run_id": request.input_data["run_id"],
            "panel_id": request.input_data["panel_id"],
            "panel_name": request.input_data["panel_name"],
            "summary": summary,
            "recommendation": recommendation,
            "score": round(positive / max(1, len(claims)), 2),
            "confidence": confidence,
            "strengths": strengths,
            "concerns": concerns,
            "affected_section_ids": request.input_data["affected_section_ids"],
            "claim_ids": [claim.claim_id for claim in claims],
            "unresolved_questions": [
                question for claim in claims for question in claim.unresolved_questions
            ][:5],
            "namespace": request.input_data["namespace"],
            "supersedes_verdict_id": request.input_data.get("supersedes_verdict_id"),
        }

    def _gatekeeper_payload(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        base = self._panel_verdict_payload(request)
        recommendation = VerdictRecommendation(base["recommendation"])
        gate_decision = GateDecision.PASS
        if recommendation == VerdictRecommendation.NEGATIVE:
            gate_decision = GateDecision.FAIL
        elif recommendation == VerdictRecommendation.MIXED:
            gate_decision = GateDecision.REVIEW
        base.update(
            {
                "gate_decision": gate_decision,
                "gate_reasons": base["strengths"][:2] + base["concerns"][:2],
            }
        )
        return base

    def _panel_lead_payload(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        panel_verdict = request.input_data.get("panel_verdict")
        if panel_verdict is None:
            raise ValueError("panel_lead requests require panel_verdict input")
        base = dict(panel_verdict)
        base["summary"] = (
            f"Lead synthesis: {base['summary']} "
            "The panel lead reconciled the judge output for memo use."
        )
        return base

    def _memo_section_update_payload(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        section_id = str(request.input_data["section_id"])
        prior_text = str(request.input_data.get("prior_text", ""))
        verdicts = [
            GatekeeperVerdict.model_validate(verdict)
            if "gate_decision" in verdict
            else PanelVerdict.model_validate(verdict)
            for verdict in request.input_data["verdicts"]
        ]
        claims = [ClaimCard.model_validate(claim) for claim in request.input_data["claims"]]
        panel_summaries = (
            "; ".join(verdict.summary for verdict in verdicts) or "No panel verdicts yet."
        )
        notable_claims = "; ".join(claim.claim for claim in claims[:2])
        stale_claims = [
            claim for claim in claims if "stale" in claim.staleness_assessment.lower()
        ]
        stale_note = ""
        if stale_claims:
            stale_note = " Stale evidence tempers conviction in this section."
        updated_text = f"{panel_summaries} Key claims: {notable_claims}{stale_note}".strip()
        if not prior_text:
            change = ChangeClassification.INITIAL
        elif prior_text == updated_text:
            change = ChangeClassification.NO_CHANGE
        else:
            change = ChangeClassification.MATERIAL_CHANGE
        return {
            "company_id": request.input_data["company_id"],
            "section_id": section_id,
            "prior_summary": prior_text,
            "updated_text": updated_text,
            "change_classification": change,
            "supporting_claim_ids": [claim.claim_id for claim in claims],
            "unresolved_items": [
                question for claim in claims for question in claim.unresolved_questions
            ][:3],
            "updated_by_run_id": request.input_data["run_id"],
        }

    def _ic_memo_payload(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        existing_sections = [
            MemoSection.model_validate(section) for section in request.input_data["sections"]
        ]
        section_lookup = {section.section_id: section for section in existing_sections}
        labels = dict(request.input_data["section_labels"])
        built_sections: list[dict[str, Any]] = []
        for section_id, label in labels.items():
            section = section_lookup.get(section_id)
            if section is None:
                section = MemoSection(
                    section_id=section_id,
                    label=label,
                    content="This section has not been advanced yet.",
                    status=MemoSectionStatus.NOT_ADVANCED,
                )
            built_sections.append(section.model_dump(mode="json"))
        overall = section_lookup.get("overall_recommendation")
        summary = overall.content if overall is not None else "Recommendation pending."
        return {
            "company_id": request.input_data["company_id"],
            "run_id": request.input_data["run_id"],
            "is_active": True,
            "is_initial_coverage": bool(request.input_data["is_initial_coverage"]),
            "sections": built_sections,
            "recommendation_summary": summary,
            "namespace": request.input_data["namespace"],
        }


def summarize_changed_sections(
    current_sections: list[MemoSection], prior_sections: list[MemoSection]
) -> Counter[str]:
    prior_map = {section.section_id: section.content for section in prior_sections}
    changes: Counter[str] = Counter()
    for section in current_sections:
        if prior_map.get(section.section_id) != section.content:
            changes[section.section_id] += 1
    return changes
