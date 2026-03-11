from __future__ import annotations

from pathlib import Path

import pytest

from ai_investing.application.services import AnalysisService, CoverageService, IngestionService
from ai_investing.domain.enums import GateDecision, RunContinueAction
from ai_investing.persistence.repositories import Repository
from ai_investing.providers.fake import FakeModelProvider


def _force_failed_gatekeeper(monkeypatch: pytest.MonkeyPatch) -> None:
    original_gatekeeper_payload = FakeModelProvider._gatekeeper_payload

    def forced_fail(self, request):
        payload = original_gatekeeper_payload(self, request)
        payload["recommendation"] = "negative"
        payload["gate_decision"] = GateDecision.FAIL
        payload["summary"] = "Gatekeepers failed the company."
        payload["gate_reasons"] = ["Customer concentration remains too high."]
        return payload

    monkeypatch.setattr(FakeModelProvider, "_gatekeeper_payload", forced_fail)


def test_tool_bundle_enforcement(seeded_acme) -> None:
    agent = next(
        agent for agent in seeded_acme.registries.agents.agents if agent.id == "demand_advocate"
    )
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        result = seeded_acme.tool_registry.execute(
            repository=repository,
            agent=agent,
            company_id="ACME",
            run_id="run_1",
            tool_id="evidence_search",
            payload={"panel_id": "demand_revenue_quality"},
        )
        assert "records" in result

        with pytest.raises(PermissionError):
            seeded_acme.tool_registry.execute(
                repository=repository,
                agent=agent,
                company_id="ACME",
                run_id="run_1",
                tool_id="send_notification",
                payload={},
            )


def test_end_to_end_fake_provider_run_requires_explicit_continue(seeded_acme) -> None:
    service = AnalysisService(seeded_acme)

    paused = service.analyze_company("ACME")

    assert paused["run"]["status"] == "awaiting_continue"
    assert paused["run"]["awaiting_continue"] is True
    assert paused["run"]["checkpoint_panel_id"] == "gatekeepers"
    assert paused["run"]["checkpoint"]["allowed_actions"] == ["stop", "continue"]
    assert paused["delta"] is None
    assert set(paused["panels"]) == {"gatekeepers"}

    resumed = service.continue_run(paused["run"]["run_id"])

    assert resumed["run"]["run_id"] == paused["run"]["run_id"]
    assert resumed["run"]["status"] == "complete"
    assert resumed["run"]["awaiting_continue"] is False
    assert set(resumed["panels"]) == {"gatekeepers", "demand_revenue_quality"}
    assert resumed["delta"] is not None
    assert resumed["delta"]["current_run_id"] == resumed["run"]["run_id"]


def test_failed_gatekeeper_can_continue_provisionally(seeded_acme, monkeypatch) -> None:
    _force_failed_gatekeeper(monkeypatch)
    service = AnalysisService(seeded_acme)

    paused = service.analyze_company("ACME")

    assert paused["run"]["status"] == "awaiting_continue"
    assert paused["run"]["gate_decision"] == "fail"
    assert paused["run"]["checkpoint"]["allowed_actions"] == [
        "stop",
        "continue_provisional",
    ]
    assert paused["delta"] is None

    resumed = service.continue_run(
        paused["run"]["run_id"],
        action=RunContinueAction.CONTINUE_PROVISIONAL,
    )

    assert resumed["run"]["status"] == "provisional"
    assert resumed["run"]["provisional"] is True
    assert resumed["run"]["gated_out"] is False
    assert "demand_revenue_quality" in resumed["panels"]
    assert resumed["delta"] is not None


def test_refresh_rerun_emits_materiality_aware_delta(seeded_acme, repo_root: Path) -> None:
    service = AnalysisService(seeded_acme)

    initial_pause = service.analyze_company("ACME")
    initial = service.continue_run(initial_pause["run"]["run_id"])

    IngestionService(seeded_acme).ingest_public_data(repo_root / "examples" / "acme_public_rerun")
    rerun_pause = service.refresh_company("ACME")

    assert rerun_pause["run"]["status"] == "awaiting_continue"
    assert rerun_pause["delta"] is None

    rerun = service.continue_run(rerun_pause["run"]["run_id"])
    delta = rerun["delta"]

    assert delta is not None
    assert delta["prior_run_id"] == initial["run"]["run_id"]
    assert delta["current_run_id"] == rerun["run"]["run_id"]
    assert "what_changed_since_last_run" in delta["changed_sections"]
    assert delta["changed_claim_ids"]


def test_run_due_coverage_skips_disabled_entries(seeded_acme) -> None:
    CoverageService(seeded_acme).disable_coverage("ACME")

    results = AnalysisService(seeded_acme).run_due_coverage()

    assert results == []


def test_rerun_persists_useful_tool_log_refs(seeded_acme, repo_root: Path) -> None:
    service = AnalysisService(seeded_acme)

    initial_pause = service.analyze_company("ACME")
    service.continue_run(initial_pause["run"]["run_id"])

    IngestionService(seeded_acme).ingest_public_data(repo_root / "examples" / "acme_public_rerun")
    rerun_pause = service.refresh_company("ACME")
    rerun = service.continue_run(rerun_pause["run"]["run_id"])

    with seeded_acme.database.session() as session:
        logs = Repository(session).list_tool_logs(rerun["run"]["run_id"])

    evidence_logs = [log for log in logs if log.tool_id in {"evidence_search", "public_doc_fetch"}]
    claim_logs = [log for log in logs if log.tool_id == "claim_search"]

    assert evidence_logs
    assert claim_logs
    assert any(ref.startswith("evidence:") for log in evidence_logs for ref in log.output_refs)
    assert any(ref.startswith("claim:") for log in claim_logs for ref in log.output_refs)
    assert all(log.output_refs != [log.tool_id] for log in evidence_logs + claim_logs)
