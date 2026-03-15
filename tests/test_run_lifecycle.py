from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from langgraph.types import Command

from ai_investing.application.services import AnalysisService, CoverageService, IngestionService
from ai_investing.domain.enums import (
    AlertLevel,
    Cadence,
    CompanyType,
    CoverageStatus,
    GateDecision,
    RunContinueAction,
    RunKind,
    RunStatus,
    VerdictRecommendation,
)
from ai_investing.domain.models import (
    CoverageEntry,
    GatekeeperVerdict,
    ICMemo,
    MonitoringDelta,
    PanelVerdict,
    RunCheckpoint,
    RunRecord,
)
from ai_investing.graphs.checkpointing import (
    _POSTGRES_SETUP_COMPLETE,
    checkpoint_config,
    graph_checkpointer,
    interrupt_payloads,
)
from ai_investing.graphs.company_refresh import build_company_refresh_graph
from ai_investing.persistence.repositories import Repository
from ai_investing.providers.fake import FakeModelProvider
from ai_investing.settings import Settings


def _set_panel_policy(context, company_id: str, panel_policy: str) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage(company_id)
        assert coverage is not None
        coverage.panel_policy = panel_policy
        repository.upsert_coverage(coverage)


def _seed_public_wave2_connectors(context, repo_root: Path) -> None:
    service = IngestionService(context)
    for connector_id in (
        "acme_market_packet",
        "acme_regulatory_packet",
        "acme_transcript_news_packet",
    ):
        service.ingest_public_data(
            repo_root / "examples" / "connectors" / connector_id,
            connector_id=connector_id,
        )


def _seed_public_expectations_connectors(context, repo_root: Path) -> None:
    _seed_public_wave2_connectors(context, repo_root)
    service = IngestionService(context)
    for connector_id in ("acme_consensus_packet", "acme_events_packet"):
        service.ingest_public_data(
            repo_root / "examples" / "connectors" / connector_id,
            connector_id=connector_id,
        )


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


def test_run_record_round_trips_checkpoint_state(context) -> None:
    run = RunRecord(
        company_id="ACME",
        run_kind=RunKind.ANALYZE,
        status=RunStatus.AWAITING_CONTINUE,
        gate_decision=GateDecision.FAIL,
        awaiting_continue=True,
        checkpoint_panel_id="gatekeepers",
        checkpoint=RunCheckpoint(
            checkpoint_panel_id="gatekeepers",
            allowed_actions=[
                RunContinueAction.STOP,
                RunContinueAction.CONTINUE_PROVISIONAL,
            ],
            provisional_required=True,
            note="Gatekeeper failed. Continue only as provisional analysis.",
        ),
        metadata={"panel_ids": ["gatekeepers", "demand_revenue_quality"]},
    )

    with context.database.session() as session:
        repository = Repository(session)
        repository.save_run(run)

    with context.database.session() as session:
        repository = Repository(session)
        stored = repository.get_run(run.run_id)

    assert stored is not None
    assert stored.status == RunStatus.AWAITING_CONTINUE
    assert stored.gate_decision == GateDecision.FAIL
    assert stored.awaiting_continue is True
    assert stored.checkpoint_panel_id == "gatekeepers"
    assert stored.checkpoint is not None
    assert stored.checkpoint.allowed_actions == [
        RunContinueAction.STOP,
        RunContinueAction.CONTINUE_PROVISIONAL,
    ]


def test_run_record_lookup_returns_terminal_lifecycle_flags(context) -> None:
    run = RunRecord(
        company_id="ACME",
        run_kind=RunKind.REFRESH,
        status=RunStatus.PROVISIONAL,
        gate_decision=GateDecision.FAIL,
        provisional=True,
        stopped_after_panel="gatekeepers",
        checkpoint_panel_id="gatekeepers",
    )

    with context.database.session() as session:
        repository = Repository(session)
        repository.save_run(run)

    with context.database.session() as session:
        repository = Repository(session)
        stored = repository.get_run(run.run_id)

    assert stored is not None
    assert stored.status == RunStatus.PROVISIONAL
    assert stored.provisional is True
    assert stored.awaiting_continue is False
    assert stored.stopped_after_panel == "gatekeepers"


def test_sqlite_context_uses_reusable_memory_checkpointer(context) -> None:
    with graph_checkpointer(context.settings) as first:
        with graph_checkpointer(context.settings) as second:
            assert first is second


def test_postgres_checkpoint_uses_psycopg_compatible_conn_string(monkeypatch) -> None:
    setup_calls: list[str] = []
    conn_strings: list[str] = []

    class FakeSaver:
        def setup(self) -> None:
            setup_calls.append("setup")

    class FakeSaverContext:
        def __enter__(self) -> FakeSaver:
            return FakeSaver()

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    class FakePostgresSaver:
        @classmethod
        def from_conn_string(cls, conn_string: str) -> FakeSaverContext:
            conn_strings.append(conn_string)
            return FakeSaverContext()

    monkeypatch.setitem(
        sys.modules,
        "langgraph.checkpoint.postgres",
        SimpleNamespace(PostgresSaver=FakePostgresSaver),
    )
    _POSTGRES_SETUP_COMPLETE.clear()

    settings = Settings(
        database_url="postgresql+psycopg://postgres:postgres@db:5432/ai_investing",
        provider="fake",
    )

    with graph_checkpointer(settings):
        pass

    assert conn_strings == ["postgresql://postgres:postgres@db:5432/ai_investing"]
    assert setup_calls == ["setup"]


def test_company_refresh_graph_auto_continues_passed_gatekeepers(context) -> None:
    runtime = StubRuntime(gate_decision=GateDecision.PASS)

    with graph_checkpointer(context.settings) as checkpointer:
        graph = build_company_refresh_graph(
            runtime=runtime,
            panel_ids=["gatekeepers", "demand_revenue_quality"],
            memo_reconciliation=True,
            monitoring_enabled=True,
            checkpointer=checkpointer,
        )
        result = graph.invoke(
            {
                "company_id": "ACME",
                "run_id": "run_pause_continue",
                "panel_ids": ["gatekeepers", "demand_revenue_quality"],
            },
            config=checkpoint_config("run_pause_continue"),
        )
        payloads = interrupt_payloads(result)

    assert payloads == []
    assert "demand_revenue_quality" in result["panel_results"]
    assert result["provisional"] is False
    assert result["memo"]["recommendation_summary"] == "memo reconciled"


def test_company_refresh_graph_routes_failed_gate_to_stop(context) -> None:
    runtime = StubRuntime(gate_decision=GateDecision.FAIL)

    with graph_checkpointer(context.settings) as checkpointer:
        graph = build_company_refresh_graph(
            runtime=runtime,
            panel_ids=["gatekeepers", "demand_revenue_quality"],
            memo_reconciliation=True,
            monitoring_enabled=True,
            checkpointer=checkpointer,
        )
        graph.invoke(
            {
                "company_id": "ACME",
                "run_id": "run_gate_stop",
                "panel_ids": ["gatekeepers", "demand_revenue_quality"],
            },
            config=checkpoint_config("run_gate_stop"),
        )
        stopped = graph.invoke(
            Command(resume={"action": "stop"}),
            config=checkpoint_config("run_gate_stop"),
        )

    assert stopped["gated_out"] is True
    assert stopped["stopped_after_panel"] == "gatekeepers"
    assert "demand_revenue_quality" not in stopped.get("panel_results", {})
    assert stopped["delta"]["change_summary"] == "monitoring complete"


def test_company_refresh_graph_routes_failed_gate_to_provisional_continue(context) -> None:
    runtime = StubRuntime(gate_decision=GateDecision.FAIL)

    with graph_checkpointer(context.settings) as checkpointer:
        graph = build_company_refresh_graph(
            runtime=runtime,
            panel_ids=["gatekeepers", "demand_revenue_quality"],
            memo_reconciliation=True,
            monitoring_enabled=True,
            checkpointer=checkpointer,
        )
        graph.invoke(
            {
                "company_id": "ACME",
                "run_id": "run_gate_provisional",
                "panel_ids": ["gatekeepers", "demand_revenue_quality"],
            },
            config=checkpoint_config("run_gate_provisional"),
        )
        resumed = graph.invoke(
            Command(resume={"action": "continue_provisional"}),
            config=checkpoint_config("run_gate_provisional"),
        )

    assert resumed["provisional"] is True
    assert resumed["gated_out"] is False
    assert "demand_revenue_quality" in resumed["panel_results"]


def test_company_refresh_graph_keeps_structured_skips_visible(context) -> None:
    runtime = StubRuntime(
        gate_decision=GateDecision.PASS,
        skipped_panels={"demand_revenue_quality"},
    )

    with graph_checkpointer(context.settings) as checkpointer:
        graph = build_company_refresh_graph(
            runtime=runtime,
            panel_ids=["gatekeepers", "demand_revenue_quality"],
            memo_reconciliation=True,
            monitoring_enabled=True,
            checkpointer=checkpointer,
        )
        result = graph.invoke(
            {
                "company_id": "ACME",
                "run_id": "run_skip_visible",
                "panel_ids": ["gatekeepers", "demand_revenue_quality"],
            },
            config=checkpoint_config("run_skip_visible"),
        )

    demand = result["panel_results"]["demand_revenue_quality"]
    assert demand["claims"] == []
    assert demand["skip"]["status"] == "skipped"
    assert demand["skip"]["reason_code"] == "missing_context"


def test_analysis_service_auto_continues_passed_gatekeepers(seeded_acme) -> None:
    service = AnalysisService(seeded_acme)

    result = service.analyze_company("ACME")

    assert result["run"]["status"] == "complete"
    assert result["run"]["awaiting_continue"] is False
    assert result["run"]["run_id"]
    assert "gatekeepers" in result["panels"]
    assert "demand_revenue_quality" in result["panels"]
    assert result["delta"] is not None
    assert result["run"]["checkpoint"]["resolution_action"] == "continue"

def test_run_due_coverage_keeps_failed_gatekeeper_runs_due_and_queryable(
    seeded_acme,
    monkeypatch,
) -> None:
    _force_failed_gatekeeper(monkeypatch)
    service = AnalysisService(seeded_acme)

    first = service.run_due_coverage()
    first_run_id = first[0]["run"]["run_id"]

    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")
        runs = repository.list_runs("ACME")

    assert coverage is not None
    assert coverage.last_run_at is None
    assert len(runs) == 1
    assert runs[0].status == RunStatus.AWAITING_CONTINUE

    second = service.run_due_coverage()

    with seeded_acme.database.session() as session:
        repository = Repository(session)
        runs = repository.list_runs("ACME")

    assert second[0]["run"]["run_id"] == first_run_id
    assert len(runs) == 1


def test_completed_scheduled_run_rolls_forward_from_next_future_slot(seeded_acme) -> None:
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")
        assert coverage is not None
        coverage.preferred_run_time = "09:30"
        coverage.next_run_at = datetime(2026, 3, 2, 14, 30, tzinfo=UTC)
        repository.upsert_coverage(coverage)

    result = AnalysisService(seeded_acme).analyze_company("ACME")

    assert result["run"]["status"] == "complete"
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")

    assert coverage is not None
    assert coverage.last_run_at is not None
    assert coverage.next_run_at == datetime(2026, 3, 16, 13, 30, tzinfo=UTC)


def test_stopped_run_does_not_advance_coverage_schedule(seeded_acme, monkeypatch) -> None:
    _force_failed_gatekeeper(monkeypatch)
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")
        assert coverage is not None
        original_next_run_at = coverage.next_run_at

    paused = AnalysisService(seeded_acme).analyze_company("ACME")
    stopped = AnalysisService(seeded_acme).continue_run(
        paused["run"]["run_id"],
        action=RunContinueAction.STOP,
    )

    assert stopped["run"]["status"] == "gated_out"
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")

    assert coverage is not None
    assert coverage.last_run_at is None
    assert coverage.next_run_at == original_next_run_at


def test_run_panel_rejects_direct_downstream_execution(seeded_acme) -> None:
    with pytest.raises(ValueError, match="gatekeepers"):
        AnalysisService(seeded_acme).run_panel("ACME", "demand_revenue_quality")


def test_run_panel_rejects_unimplemented_scaffold_panel(seeded_acme) -> None:
    with pytest.raises(ValueError, match=r"Runs must begin at gatekeepers\."):
        AnalysisService(seeded_acme).run_panel("ACME", "supply_product_operations")

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


def test_refresh_company_runs_full_surface_with_explicit_overlay_skips(
    seeded_acme,
    repo_root: Path,
) -> None:
    _set_panel_policy(seeded_acme, "ACME", "full_surface")
    analysis = AnalysisService(seeded_acme)
    initial = analysis.analyze_company("ACME")
    refreshed = analysis.refresh_company("ACME")

    assert initial["run"]["status"] == "complete"
    assert refreshed["run"]["status"] == "complete"
    assert refreshed["delta"] is not None
    assert refreshed["panels"]["security_or_deal_overlay"]["support"]["status"] == "unsupported"
    assert refreshed["panels"]["portfolio_fit_positioning"]["support"]["status"] == "unsupported"
    assert (
        refreshed["panels"]["security_or_deal_overlay"]["skip"]["reason_code"]
        == "missing_context"
    )
    assert (
        refreshed["panels"]["portfolio_fit_positioning"]["skip"]["reason_code"]
        == "missing_context"
    )

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert len(runs) == 2


def test_refresh_company_keeps_market_macro_regulatory_support_visible(
    seeded_acme,
    repo_root: Path,
) -> None:
    _seed_public_wave2_connectors(seeded_acme, repo_root)
    analysis = AnalysisService(seeded_acme)
    _set_panel_policy(seeded_acme, "ACME", "external_company_quality")
    initial = analysis.analyze_company("ACME")
    refreshed = analysis.refresh_company("ACME")

    assert initial["panels"]["demand_revenue_quality"]["support"]["status"] == "supported"
    assert initial["panels"]["supply_product_operations"]["support"]["status"] == "supported"
    assert initial["panels"]["market_structure_growth"]["support"]["status"] == "supported"
    assert refreshed["delta"] is not None
    assert refreshed["panels"]["demand_revenue_quality"]["support"]["status"] == "supported"
    assert refreshed["panels"]["supply_product_operations"]["support"]["status"] == "supported"
    assert refreshed["panels"]["market_structure_growth"]["support"]["status"] == "supported"
    assert refreshed["panels"]["macro_industry_transmission"]["support"]["status"] == "supported"
    assert (
        refreshed["panels"]["external_regulatory_geopolitical"]["support"]["status"]
        == "supported"
    )


def test_external_company_quality_refresh_stays_narrower_than_full_surface(
    seeded_acme,
    repo_root: Path,
) -> None:
    _seed_public_wave2_connectors(seeded_acme, repo_root)
    analysis = AnalysisService(seeded_acme)
    _set_panel_policy(seeded_acme, "ACME", "external_company_quality")

    result = analysis.refresh_company("ACME")

    assert result["run"]["status"] == "complete"
    assert "expectations_catalyst_realization" not in result["panels"]
    assert "security_or_deal_overlay" not in result["panels"]
    assert "portfolio_fit_positioning" not in result["panels"]
    assert result["delta"] is not None
    assert "what_changed_since_last_run" in result["delta"]["changed_sections"]


def test_expectations_rollout_refresh_keeps_expectations_support_visible(
    seeded_acme,
    repo_root: Path,
) -> None:
    analysis = AnalysisService(seeded_acme)
    _set_panel_policy(seeded_acme, "ACME", "expectations_rollout")
    initial = analysis.analyze_company("ACME")
    refreshed = analysis.refresh_company("ACME")

    assert (
        initial["panels"]["expectations_catalyst_realization"]["support"]["status"]
        == "supported"
    )
    assert refreshed["delta"] is not None
    assert (
        refreshed["panels"]["expectations_catalyst_realization"]["support"]["status"]
        == "supported"
    )
    assert "skip" not in refreshed["panels"]["expectations_catalyst_realization"]


def test_expectations_rollout_refresh_surfaces_skip_when_inputs_are_missing(
    context,
    repo_root: Path,
) -> None:
    """Use intentionally limited fixture: wave2 connectors only, no expectations evidence."""
    _seed_public_wave2_connectors(context, repo_root)
    CoverageService(context).add_coverage(
        CoverageEntry(
            company_id="ACME",
            company_name="Acme Cloud",
            company_type=CompanyType.PUBLIC,
            coverage_status=CoverageStatus.WATCHLIST,
            cadence=Cadence.WEEKLY,
        )
    )
    analysis = AnalysisService(context)
    _set_panel_policy(context, "ACME", "expectations_rollout")

    result = analysis.refresh_company("ACME")

    assert result["run"]["status"] == "complete"
    assert (
        result["panels"]["expectations_catalyst_realization"]["support"]["status"]
        == "unsupported"
    )
    assert result["panels"]["expectations_catalyst_realization"]["skip"]["reason_code"] == (
        "missing_evidence_families"
    )


class StubContext:
    def __init__(self) -> None:
        self._panels = {
            "gatekeepers": SimpleNamespace(
                id="gatekeepers",
                name="Gatekeepers",
                subgraph="gatekeeper",
            ),
            "demand_revenue_quality": SimpleNamespace(
                id="demand_revenue_quality",
                name="Demand And Revenue Quality",
                subgraph="debate",
            ),
        }

    def get_panel(self, panel_id: str):
        return self._panels[panel_id]


class StubRuntime:
    def __init__(
        self,
        *,
        gate_decision: GateDecision,
        skipped_panels: set[str] | None = None,
    ) -> None:
        self.context = StubContext()
        self.gate_decision = gate_decision
        self.skipped_panels = skipped_panels or set()

    def execute_panel(self, panel_id: str) -> dict[str, object]:
        if panel_id in self.skipped_panels:
            return {
                "claims": [],
                "skip": {
                    "panel_id": panel_id,
                    "panel_name": "Demand And Revenue Quality",
                    "company_type": "public",
                    "status": "skipped",
                    "reason_code": "missing_context",
                    "reason": (
                        "Demand And Revenue Quality requires run context that is "
                        "missing: portfolio_context."
                    ),
                    "evidence_summary": (
                        "0 records matched this panel; evidence families: none; "
                        "factor coverage ratio: 0.00."
                    ),
                    "evidence_count": 0,
                    "factor_coverage_ratio": 0.0,
                    "available_evidence_families": [],
                    "missing_evidence_families": [],
                    "required_context": ["portfolio_context"],
                    "missing_context": ["portfolio_context"],
                },
                "support": {
                    "panel_id": panel_id,
                    "panel_name": "Demand And Revenue Quality",
                    "company_type": "public",
                    "status": "unsupported",
                    "reason": (
                        "Demand And Revenue Quality requires run context that is "
                        "missing: portfolio_context."
                    ),
                    "evidence_count": 0,
                    "factor_coverage_ratio": 0.0,
                    "evidence_summary": (
                        "0 records matched this panel; evidence families: none; "
                        "factor coverage ratio: 0.00."
                    ),
                    "available_evidence_families": [],
                    "missing_evidence_families": [],
                    "required_context": ["portfolio_context"],
                    "missing_context": ["portfolio_context"],
                    "weak_confidence_allowed": False,
                },
            }
        if panel_id == "gatekeepers":
            verdict = GatekeeperVerdict(
                company_id="ACME",
                company_type=CompanyType.PUBLIC,
                run_id="run_stub",
                panel_id="gatekeepers",
                panel_name="Gatekeepers",
                summary="Gatekeepers complete",
                recommendation=(
                    VerdictRecommendation.NEGATIVE
                    if self.gate_decision == GateDecision.FAIL
                    else VerdictRecommendation.POSITIVE
                ),
                score=0.7,
                confidence=0.8,
                namespace="company/ACME/verdicts/gatekeepers",
                gate_decision=self.gate_decision,
                gate_reasons=["reason"],
            )
        else:
            verdict = PanelVerdict(
                company_id="ACME",
                company_type=CompanyType.PUBLIC,
                run_id="run_stub",
                panel_id=panel_id,
                panel_name="Demand And Revenue Quality",
                summary="Demand review complete",
                recommendation=VerdictRecommendation.POSITIVE,
                score=0.8,
                confidence=0.8,
                namespace=f"company/ACME/verdicts/{panel_id}",
            )
        return {
            "claims": [],
            "verdict": verdict.model_dump(mode="json"),
            "support": {
                "panel_id": panel_id,
                "panel_name": verdict.panel_name,
                "company_type": "public",
                "status": "supported",
                "reason": "Panel support requirements are satisfied for this run.",
                "evidence_count": 2,
                "factor_coverage_ratio": 1.0,
                "evidence_summary": (
                    "2 records matched this panel; evidence families: regulatory, "
                    "transcript; factor coverage ratio: 1.00."
                ),
                "available_evidence_families": ["regulatory", "transcript"],
                "missing_evidence_families": [],
                "required_context": [],
                "missing_context": [],
                "weak_confidence_allowed": True,
            },
        }

    def finalize_panel_verdict(self, *, panel_id: str, verdict, support_payload=None):
        return verdict

    def update_memo_for_panel(self, panel_id: str) -> dict[str, object]:
        return {"memo": {"last_updated_panel": panel_id}}

    def compute_monitoring_delta(self) -> MonitoringDelta:
        return MonitoringDelta(
            company_id="ACME",
            current_run_id="run_stub",
            change_summary="monitoring complete",
            alert_level=AlertLevel.LOW,
        )

    def skip_monitoring_delta(self) -> MonitoringDelta:
        return MonitoringDelta(
            company_id="ACME",
            current_run_id="run_stub",
            change_summary="monitoring skipped",
            alert_level=AlertLevel.LOW,
        )

    def reconcile_ic_memo(self) -> ICMemo:
        return ICMemo(
            company_id="ACME",
            run_id="run_stub",
            sections=[],
            recommendation_summary="memo reconciled",
            namespace="company/ACME/memos/current",
        )

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
        return RunCheckpoint(
            checkpoint_panel_id="gatekeepers",
            allowed_actions=allowed_actions,
            provisional_required=gatekeeper.gate_decision == GateDecision.FAIL,
            note="checkpoint ready",
        )

    def auto_continue_gatekeeper(
        self,
        *,
        gatekeeper: GatekeeperVerdict,
        has_downstream_panels: bool,
    ) -> dict[str, object]:
        return {
            "gate_decision": gatekeeper.gate_decision.value,
            "awaiting_continue": False,
            "gated_out": False,
            "provisional": False,
            "stopped_after_panel": None,
            "checkpoint_panel_id": "gatekeepers",
            "resume_action": RunContinueAction.CONTINUE.value,
        }

    def resolve_gatekeeper_action(
        self,
        *,
        action: RunContinueAction,
        gatekeeper: GatekeeperVerdict,
        has_downstream_panels: bool,
    ) -> dict[str, object]:
        if action != RunContinueAction.STOP and not has_downstream_panels:
            raise ValueError("No downstream panels available after gatekeepers.")
        if gatekeeper.gate_decision == GateDecision.FAIL and action == RunContinueAction.CONTINUE:
            raise ValueError("Failed gatekeepers must resume as provisional.")
        return {
            "gate_decision": gatekeeper.gate_decision.value,
            "awaiting_continue": False,
            "gated_out": (
                action == RunContinueAction.STOP
                and gatekeeper.gate_decision == GateDecision.FAIL
            ),
            "provisional": action == RunContinueAction.CONTINUE_PROVISIONAL,
            "stopped_after_panel": "gatekeepers" if action == RunContinueAction.STOP else None,
            "checkpoint_panel_id": "gatekeepers",
            "resume_action": action.value,
        }
