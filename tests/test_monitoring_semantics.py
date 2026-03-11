from __future__ import annotations

from ai_investing.application.services import AnalysisService
from ai_investing.domain.enums import GateDecision, RunContinueAction
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


def test_memo_projects_full_contract_for_gatekeeper_pause(seeded_acme) -> None:
    result = AnalysisService(seeded_acme).analyze_company("ACME")

    sections = _section_map(result)

    assert len(sections) == 11
    assert sections["investment_snapshot"]["status"] == "refreshed"
    assert sections["growth"]["status"] == "not_advanced"
    assert "deeper panel work has not advanced this section yet" in sections["growth"]["content"]


def test_memo_marks_carried_forward_sections_stale_on_rerun_pause(seeded_acme) -> None:
    service = AnalysisService(seeded_acme)

    first = service.analyze_company("ACME")
    service.continue_run(first["run"]["run_id"])
    rerun = service.refresh_company("ACME")

    sections = _section_map(rerun)

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
