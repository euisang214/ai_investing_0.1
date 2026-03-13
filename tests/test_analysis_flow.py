from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_investing.application.services import AnalysisService, CoverageService, IngestionService
from ai_investing.domain.enums import (
    Cadence,
    CompanyType,
    CoverageStatus,
    GateDecision,
    RunContinueAction,
)
from ai_investing.domain.models import CoverageEntry
from ai_investing.persistence.repositories import Repository
from ai_investing.providers.fake import FakeModelProvider


def _memo_section_map(result: dict[str, object]) -> dict[str, dict[str, object]]:
    memo = result["memo"]
    assert isinstance(memo, dict)
    sections = memo["sections"]
    assert isinstance(sections, list)
    return {section["section_id"]: section for section in sections}


def _clear_run_baseline_metadata(context, run_id: str) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        run = repository.get_run(run_id)
        assert run is not None
        run.metadata = {
            key: value
            for key, value in run.metadata.items()
            if key
            not in {"baseline_memo", "baseline_active_claims", "baseline_active_verdicts"}
        }
        repository.save_run(run)


def _set_panel_policy(context, company_id: str, panel_policy: str) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage(company_id)
        assert coverage is not None
        coverage.panel_policy = panel_policy
        repository.upsert_coverage(coverage)


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
    assert resumed["delta"]["prior_run_id"] is None
    assert resumed["delta"]["change_summary"] == "Initial coverage run. No prior memo exists."
    assert resumed["memo"]["is_initial_coverage"] is True
    sections = _memo_section_map(resumed)
    assert sections["economic_spread"]["status"] == "not_advanced"
    assert "Stale from the prior active memo." not in sections["economic_spread"]["content"]
    assert sections["valuation_terms"]["status"] == "not_advanced"


def test_full_surface_policy_loads_but_blocks_execution_before_run_creation(seeded_acme) -> None:
    policy = seeded_acme.registries.run_policies.run_policies["full_surface"]

    assert "supply_product_operations" in policy.default_panel_ids
    assert policy.allow_unimplemented_panels is False

    _set_panel_policy(seeded_acme, "ACME", "full_surface")

    with pytest.raises(
        ValueError,
        match=r"Panel supply_product_operations is not implemented for policy full_surface\.",
    ):
        AnalysisService(seeded_acme).analyze_company("ACME")

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


def test_analyze_company_rejects_explicit_scaffold_panel_selection(seeded_acme) -> None:
    with pytest.raises(
        ValueError,
        match=r"Panel supply_product_operations is not implemented for policy weekly_default\.",
    ):
        AnalysisService(seeded_acme).analyze_company(
            "ACME",
            panel_ids=["gatekeepers", "supply_product_operations"],
        )

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


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
    assert rerun["memo"]["is_initial_coverage"] is False


def test_legacy_paused_run_without_baseline_metadata_does_not_self_baseline(seeded_acme) -> None:
    service = AnalysisService(seeded_acme)

    paused = service.analyze_company("ACME")
    _clear_run_baseline_metadata(seeded_acme, paused["run"]["run_id"])

    resumed = service.continue_run(paused["run"]["run_id"])

    assert resumed["memo"]["is_initial_coverage"] is True
    assert resumed["delta"]["prior_run_id"] is None
    assert resumed["delta"]["current_run_id"] == paused["run"]["run_id"]
    assert resumed["delta"]["change_summary"] == "Initial coverage run. No prior memo exists."


def test_legacy_rerun_resume_recovers_prior_history_excluding_current_run(
    seeded_acme, repo_root: Path
) -> None:
    service = AnalysisService(seeded_acme)

    initial_pause = service.analyze_company("ACME")
    initial = service.continue_run(initial_pause["run"]["run_id"])

    IngestionService(seeded_acme).ingest_public_data(repo_root / "examples" / "acme_public_rerun")
    rerun_pause = service.refresh_company("ACME")
    _clear_run_baseline_metadata(seeded_acme, rerun_pause["run"]["run_id"])

    rerun = service.continue_run(rerun_pause["run"]["run_id"])

    assert rerun["delta"]["prior_run_id"] == initial["run"]["run_id"]
    assert rerun["delta"]["current_run_id"] == rerun["run"]["run_id"]
    assert rerun["memo"]["is_initial_coverage"] is False


def test_run_due_coverage_skips_disabled_entries(seeded_acme) -> None:
    CoverageService(seeded_acme).disable_coverage("ACME")

    results = AnalysisService(seeded_acme).run_due_coverage()

    assert results == []


def test_schedule_policy_adds_future_next_run_at_for_non_legacy_coverage(context) -> None:
    entry = CoverageService(context).add_coverage(
        CoverageEntry(
            company_id="SCHED",
            company_name="Schedule Test Co",
            company_type=CompanyType.PUBLIC,
            coverage_status=CoverageStatus.WATCHLIST,
            schedule_policy_id="biweekly",
            preferred_run_time="09:30",
        )
    )

    assert entry.cadence == Cadence.WEEKLY
    assert entry.schedule_enabled is True
    assert entry.schedule_policy_id == "biweekly"
    assert entry.preferred_run_time == "09:30"
    assert entry.next_run_at == datetime(2026, 3, 16, 13, 30, tzinfo=UTC)


def test_schedule_disabled_manual_run_clears_next_run_at_after_completion(seeded_acme) -> None:
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")
        assert coverage is not None
        coverage.schedule_enabled = False
        coverage.next_run_at = datetime(2026, 3, 11, 9, 0, tzinfo=UTC)
        repository.upsert_coverage(coverage)

    paused = AnalysisService(seeded_acme).analyze_company("ACME")
    resumed = AnalysisService(seeded_acme).continue_run(paused["run"]["run_id"])

    assert resumed["run"]["status"] == "complete"
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")

    assert coverage is not None
    assert coverage.schedule_enabled is False
    assert coverage.last_run_at is not None
    assert coverage.next_run_at is None


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


def test_required_public_connector_evidence_is_compatible_with_analysis_flow(
    context,
    repo_root: Path,
) -> None:
    service = IngestionService(context)
    for connector_id in (
        "acme_regulatory_packet",
        "acme_market_packet",
        "acme_consensus_packet",
        "acme_ownership_packet",
    ):
        service.ingest_public_data(
            repo_root / "examples" / "connectors" / connector_id,
            connector_id=connector_id,
        )

    CoverageService(context).add_coverage(
        CoverageEntry(
            company_id="ACME",
            company_name="Acme Cloud",
            company_type=CompanyType.PUBLIC,
            coverage_status=CoverageStatus.WATCHLIST,
            cadence=Cadence.WEEKLY,
        )
    )

    paused = AnalysisService(context).analyze_company("ACME")
    resumed = AnalysisService(context).continue_run(paused["run"]["run_id"])

    assert paused["run"]["status"] == "awaiting_continue"
    assert resumed["run"]["status"] == "complete"
    with context.database.session() as session:
        repository = Repository(session)
        evidence = repository.list_evidence("ACME")
        claims = repository.list_claim_cards("ACME", run_id=resumed["run"]["run_id"])
        verdicts = repository.list_panel_verdicts(
            "ACME", run_id=resumed["run"]["run_id"]
        )

    assert any(record.metadata.get("evidence_family") == "regulatory" for record in evidence)
    assert any(record.metadata.get("evidence_family") == "consensus" for record in evidence)
    assert claims
    assert verdicts


def test_dataroom_evidence_is_compatible_with_private_analysis_flow(
    context,
    repo_root: Path,
) -> None:
    service = IngestionService(context)
    for connector_id in ("beta_dataroom", "beta_kpi_packet"):
        service.ingest_private_data(
            repo_root / "examples" / "connectors" / connector_id,
            connector_id=connector_id,
        )

    CoverageService(context).add_coverage(
        CoverageEntry(
            company_id="BETA",
            company_name="Beta Logistics Software",
            company_type=CompanyType.PRIVATE,
            coverage_status=CoverageStatus.WATCHLIST,
            cadence=Cadence.WEEKLY,
        )
    )

    paused = AnalysisService(context).analyze_company("BETA")
    resumed = AnalysisService(context).continue_run(paused["run"]["run_id"])

    assert paused["run"]["status"] == "awaiting_continue"
    assert resumed["run"]["status"] == "complete"
    with context.database.session() as session:
        repository = Repository(session)
        evidence = repository.list_evidence("BETA")
        claims = repository.list_claim_cards("BETA", run_id=resumed["run"]["run_id"])

    assert any(record.metadata.get("evidence_family") == "dataroom" for record in evidence)
    assert any(record.metadata.get("evidence_family") == "kpi_packet" for record in evidence)
    assert claims
