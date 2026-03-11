from __future__ import annotations

from datetime import UTC, datetime

from ai_investing.application.services import AnalysisService, RefreshRuntime
from ai_investing.domain.enums import (
    AlertLevel,
    CompanyType,
    GateDecision,
    MemoSectionStatus,
    RunContinueAction,
    RunKind,
    RunStatus,
    VerdictRecommendation,
)
from ai_investing.domain.models import (
    ClaimCard,
    EvidenceRecord,
    FactorSignal,
    GatekeeperVerdict,
    ICMemo,
    MemoSection,
    MemoSectionUpdate,
    RunRecord,
    SourceRef,
    StructuredGenerationRequest,
)
from ai_investing.persistence.repositories import Repository
from ai_investing.providers.fake import FakeModelProvider


def _section_map(result: dict[str, object]) -> dict[str, dict[str, object]]:
    memo = result["memo"]
    assert isinstance(memo, dict)
    sections = memo["sections"]
    assert isinstance(sections, list)
    return {
        section["section_id"]: section
        for section in sections
        if isinstance(section, dict) and "section_id" in section
    }


def _claim(
    *,
    run_id: str,
    claim_text: str,
    confidence: float,
    section_ids: list[str],
    factor_id: str = "customer_concentration",
    staleness_assessment: str = "Fresh enough for current memo update.",
) -> ClaimCard:
    return ClaimCard(
        company_id="ACME",
        company_type=CompanyType.PUBLIC,
        run_id=run_id,
        panel_id="demand_revenue_quality",
        factor_id=factor_id,
        agent_id="demand_advocate",
        claim=claim_text,
        bull_case="Bull case unchanged.",
        bear_case="Bear case unchanged.",
        confidence=confidence,
        evidence_quality=0.8,
        staleness_assessment=staleness_assessment,
        time_horizon="12-24 months",
        durability_horizon="multi-year",
        what_changed="No material change.",
        namespace=f"company/ACME/claims/{factor_id}",
        section_impacts=[
            {
                "section_id": section_id,
                "rationale": f"{factor_id} affects {section_id}.",
            }
            for section_id in section_ids
        ],
    )


def _memo_section(
    *,
    section_id: str,
    content: str,
    run_id: str,
    status: MemoSectionStatus = MemoSectionStatus.REFRESHED,
) -> MemoSection:
    return MemoSection(
        section_id=section_id,
        label=section_id.replace("_", " "),
        content=content,
        status=status,
        updated_by_run_id=run_id,
    )


def _gatekeeper_verdict(*, run_id: str, gate_decision: GateDecision) -> GatekeeperVerdict:
    recommendation_map = {
        GateDecision.PASS: VerdictRecommendation.POSITIVE,
        GateDecision.REVIEW: VerdictRecommendation.MIXED,
        GateDecision.FAIL: VerdictRecommendation.NEGATIVE,
    }
    return GatekeeperVerdict(
        company_id="ACME",
        company_type=CompanyType.PUBLIC,
        run_id=run_id,
        panel_id="gatekeepers",
        panel_name="Gatekeepers",
        summary=f"Gatekeepers {gate_decision.value}.",
        recommendation=recommendation_map[gate_decision],
        score=0.5,
        confidence=0.7,
        affected_section_ids=["investment_snapshot", "risk", "overall_recommendation"],
        claim_ids=[],
        namespace="company/ACME/verdicts/gatekeepers",
        gate_decision=gate_decision,
        gate_reasons=["reason"],
    )


def _runtime_for_delta(
    seeded_acme,
    *,
    prior_claims: list[ClaimCard],
    current_claims: list[ClaimCard],
    prior_sections: list[MemoSection],
    current_sections: list[MemoSection],
    prior_gate_decision: GateDecision | None = None,
    current_gate_decision: GateDecision | None = None,
) -> RefreshRuntime:
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")
        company_profile = repository.get_company_profile("ACME")

    assert coverage is not None
    assert company_profile is not None

    run = RunRecord(
        company_id="ACME",
        run_kind=RunKind.REFRESH,
        status=RunStatus.RUNNING,
    )
    prior_memo = ICMemo(
        company_id="ACME",
        run_id="run_prior",
        sections=prior_sections,
        recommendation_summary="Prior memo.",
        namespace="company/ACME/memos/current",
    )
    prior_verdicts = (
        {"gatekeepers": _gatekeeper_verdict(run_id="run_prior", gate_decision=prior_gate_decision)}
        if prior_gate_decision is not None
        else {}
    )
    current_verdicts = (
        {"gatekeepers": _gatekeeper_verdict(run_id=run.run_id, gate_decision=current_gate_decision)}
        if current_gate_decision is not None
        else {}
    )
    return RefreshRuntime(
        context=seeded_acme,
        run=run,
        coverage=coverage,
        company_profile=company_profile,
        prior_memo=prior_memo,
        prior_active_claims=prior_claims,
        prior_active_verdicts=prior_verdicts,
        current_sections={section.section_id: section for section in current_sections},
        current_claims=current_claims,
        current_verdicts=current_verdicts,
    )


def _evidence_record(*, staleness_days: int, factor_id: str) -> EvidenceRecord:
    return EvidenceRecord(
        company_id="ACME",
        company_type=CompanyType.PUBLIC,
        source_type="public_filing",
        title=f"{factor_id} evidence",
        body="Evidence body.",
        source_path="fixtures/source.txt",
        namespace="company/ACME/evidence",
        panel_ids=["gatekeepers"],
        factor_ids=[factor_id],
        factor_signals={
            factor_id: FactorSignal(
                stance="positive",
                summary=f"{factor_id} remains supportive.",
            )
        },
        source_refs=[SourceRef(label="Form 10-K")],
        evidence_quality=0.8,
        staleness_days=staleness_days,
        as_of_date=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _claim_request(*, run_id: str, evidence: list[EvidenceRecord]) -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        task_type="claim_card",
        prompt="",
        input_data={
            "company_id": "ACME",
            "company_name": "Acme Cloud",
            "company_type": "public",
            "run_id": run_id,
            "panel_id": "gatekeepers",
            "factor_id": "balance_sheet_survivability",
            "factor_name": "Balance Sheet Survivability",
            "agent_id": "gatekeeper_advocate",
            "role_type": "specialist",
            "evidence": [record.model_dump(mode="json") for record in evidence],
            "prior_claim": "",
            "section_ids": ["risk", "overall_recommendation"],
            "namespace": "company/ACME/claims/balance_sheet_survivability",
        },
    )


def test_memo_projects_full_contract_for_gatekeeper_pause(seeded_acme) -> None:
    result = AnalysisService(seeded_acme).analyze_company("ACME")

    sections = _section_map(result)

    assert len(sections) == 11
    assert sections["investment_snapshot"]["status"] == "refreshed"
    assert sections["growth"]["status"] == "not_advanced"
    assert "deeper panel work has not advanced this section yet" in sections["growth"]["content"]


def test_memo_keeps_same_run_placeholders_not_advanced_on_first_completion(seeded_acme) -> None:
    service = AnalysisService(seeded_acme)

    paused = service.analyze_company("ACME")
    completed = service.continue_run(paused["run"]["run_id"])
    sections = _section_map(completed)

    assert completed["memo"]["is_initial_coverage"] is True
    assert completed["delta"]["prior_run_id"] is None
    assert sections["economic_spread"]["status"] == "not_advanced"
    assert sections["valuation_terms"]["status"] == "not_advanced"
    assert "Stale from the prior active memo." not in sections["economic_spread"]["content"]
    assert sections["what_changed_since_last_run"]["content"] == (
        "Initial coverage run. No prior memo exists."
    )


def test_memo_marks_carried_forward_sections_stale_on_rerun_pause(seeded_acme) -> None:
    service = AnalysisService(seeded_acme)

    first = service.analyze_company("ACME")
    service.continue_run(first["run"]["run_id"])
    rerun = service.refresh_company("ACME")

    sections = _section_map(rerun)

    assert rerun["memo"]["is_initial_coverage"] is False
    assert sections["growth"]["status"] == "stale"
    assert "Carried forward from the prior memo" in sections["growth"]["content"]


def test_memo_keeps_provisional_language_after_failed_gatekeeper_override(
    seeded_acme, monkeypatch
) -> None:
    original_gatekeeper_payload = FakeModelProvider._gatekeeper_payload

    def forced_fail(self, request):
        payload = original_gatekeeper_payload(self, request)
        payload["recommendation"] = "negative"
        payload["gate_decision"] = GateDecision.FAIL
        payload["summary"] = "Gatekeepers failed the company."
        return payload

    monkeypatch.setattr(FakeModelProvider, "_gatekeeper_payload", forced_fail)

    service = AnalysisService(seeded_acme)
    paused = service.analyze_company("ACME")
    resumed = service.continue_run(
        paused["run"]["run_id"],
        RunContinueAction.CONTINUE_PROVISIONAL,
    )

    sections = _section_map(resumed)

    assert paused["run"]["gate_decision"] == GateDecision.FAIL
    assert resumed["run"]["status"] == "provisional"
    assert sections["overall_recommendation"]["status"] == "refreshed"
    assert sections["overall_recommendation"]["content"].startswith(
        "Provisional after failed gatekeeper override."
    )


def test_delta_refreshes_run_log_for_low_material_fake_provider_rerun(
    seeded_acme, monkeypatch
) -> None:
    service = AnalysisService(seeded_acme)

    first = service.analyze_company("ACME")
    service.continue_run(first["run"]["run_id"])

    original_claim_payload = FakeModelProvider._claim_card_payload

    def low_material_confidence_shift(self, request):
        payload = original_claim_payload(self, request)
        payload["confidence"] = round(min(0.99, payload["confidence"] + 0.04), 2)
        return payload

    monkeypatch.setattr(
        FakeModelProvider,
        "_claim_card_payload",
        low_material_confidence_shift,
    )

    rerun = service.refresh_company("ACME")
    completed = service.continue_run(rerun["run"]["run_id"])
    sections = _section_map(completed)

    assert completed["delta"]["alert_level"] == "medium"
    assert completed["delta"]["changed_sections"] == [
        "economic_spread",
        "expectations_variant_view",
        "portfolio_fit_positioning",
        "realization_path_catalysts",
        "valuation_terms",
        "what_changed_since_last_run",
    ]
    assert "Material sections: economic_spread" in completed["delta"]["change_summary"]
    assert sections["what_changed_since_last_run"]["status"] == "refreshed"


def test_delta_ignores_sub_material_confidence_only_changes(seeded_acme) -> None:
    prior_claim = _claim(
        run_id="run_prior",
        claim_text="ACME appears stable on demand quality.",
        confidence=0.7,
        section_ids=["investment_snapshot"],
    )
    current_claim = _claim(
        run_id="run_current",
        claim_text="ACME appears stable on demand quality.",
        confidence=0.74,
        section_ids=["investment_snapshot"],
    )
    runtime = _runtime_for_delta(
        seeded_acme,
        prior_claims=[prior_claim],
        current_claims=[current_claim],
        prior_sections=[
            _memo_section(
                section_id="investment_snapshot",
                content="Demand remains steady.",
                run_id="run_prior",
            )
        ],
        current_sections=[
            _memo_section(
                section_id="investment_snapshot",
                content="Demand remains steady.",
                run_id="run_current",
            )
        ],
    )

    delta = runtime.compute_monitoring_delta()

    assert delta.changed_claim_ids == []
    assert delta.changed_sections == ["what_changed_since_last_run"]
    assert delta.alert_level == AlertLevel.LOW


def test_delta_escalates_gatekeeper_change_to_high_alert(seeded_acme) -> None:
    runtime = _runtime_for_delta(
        seeded_acme,
        prior_claims=[],
        current_claims=[],
        prior_sections=[
            _memo_section(
                section_id="investment_snapshot",
                content="Snapshot was investable.",
                run_id="run_prior",
            ),
            _memo_section(section_id="risk", content="Risk was manageable.", run_id="run_prior"),
            _memo_section(
                section_id="overall_recommendation",
                content="Recommendation was positive.",
                run_id="run_prior",
            ),
        ],
        current_sections=[
            _memo_section(
                section_id="investment_snapshot",
                content="Snapshot is blocked pending review.",
                run_id="run_current",
            ),
            _memo_section(section_id="risk", content="Risk is elevated.", run_id="run_current"),
            _memo_section(
                section_id="overall_recommendation",
                content="Recommendation is blocked pending review.",
                run_id="run_current",
            ),
        ],
        prior_gate_decision=GateDecision.PASS,
        current_gate_decision=GateDecision.FAIL,
    )

    delta = runtime.compute_monitoring_delta()

    assert delta.alert_level == AlertLevel.HIGH
    assert {
        "investment_snapshot",
        "overall_recommendation",
        "risk",
    }.issubset(delta.changed_sections)
    assert "Gatekeeper decision changed." in delta.change_summary


def test_stale_fake_provider_claims_lower_confidence() -> None:
    provider = FakeModelProvider()

    fresh_claim = provider.generate_structured(
        _claim_request(
            run_id="run_fresh",
            evidence=[_evidence_record(staleness_days=5, factor_id="balance_sheet_survivability")],
        ),
        ClaimCard,
    )
    stale_claim = provider.generate_structured(
        _claim_request(
            run_id="run_stale",
            evidence=[
                _evidence_record(
                    staleness_days=120,
                    factor_id="balance_sheet_survivability",
                )
            ],
        ),
        ClaimCard,
    )

    assert stale_claim.confidence < fresh_claim.confidence
    assert "stale evidence" in stale_claim.staleness_assessment.lower()


def test_stale_memo_updates_call_out_tempered_conviction() -> None:
    provider = FakeModelProvider()
    stale_claim = provider.generate_structured(
        _claim_request(
            run_id="run_stale",
            evidence=[
                _evidence_record(
                    staleness_days=120,
                    factor_id="balance_sheet_survivability",
                )
            ],
        ),
        ClaimCard,
    )
    update = provider.generate_structured(
        StructuredGenerationRequest(
            task_type="memo_section_update",
            prompt="",
            input_data={
                "company_id": "ACME",
                "run_id": "run_stale",
                "section_id": "risk",
                "prior_text": "",
                "verdicts": [
                    _gatekeeper_verdict(
                        run_id="run_stale",
                        gate_decision=GateDecision.PASS,
                    ).model_dump(mode="json")
                ],
                "claims": [stale_claim.model_dump(mode="json")],
            },
        ),
        MemoSectionUpdate,
    )

    assert "tempers conviction" in update.updated_text.lower()


def test_tool_logs_capture_record_level_output_refs(seeded_acme) -> None:
    service = AnalysisService(seeded_acme)

    first = service.analyze_company("ACME")
    service.continue_run(first["run"]["run_id"])
    rerun = service.refresh_company("ACME")

    with seeded_acme.database.session() as session:
        logs = Repository(session).list_tool_logs(rerun["run"]["run_id"])

    evidence_logs = [log for log in logs if log.tool_id == "evidence_search"]
    claim_logs = [log for log in logs if log.tool_id == "claim_search"]

    assert evidence_logs
    assert claim_logs
    assert any(ref.startswith("evidence:") for log in evidence_logs for ref in log.output_refs)
    assert any(ref.startswith("claim:") for log in claim_logs for ref in log.output_refs)
    assert all(log.output_refs != ["evidence_search"] for log in evidence_logs)
    assert all(log.output_refs != ["claim_search"] for log in claim_logs)
