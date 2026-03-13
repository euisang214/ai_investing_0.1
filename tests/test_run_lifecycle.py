from __future__ import annotations

import sys
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from langgraph.types import Command

from ai_investing.application.services import AnalysisService
from ai_investing.domain.enums import (
    AlertLevel,
    CompanyType,
    GateDecision,
    RunContinueAction,
    RunKind,
    RunStatus,
    VerdictRecommendation,
)
from ai_investing.domain.models import (
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
from ai_investing.settings import Settings


def _set_panel_policy(context, company_id: str, panel_policy: str) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage(company_id)
        assert coverage is not None
        coverage.panel_policy = panel_policy
        repository.upsert_coverage(coverage)


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


def test_company_refresh_graph_pauses_after_gatekeepers_and_resumes_continue(context) -> None:
    runtime = StubRuntime(gate_decision=GateDecision.PASS)

    with graph_checkpointer(context.settings) as checkpointer:
        graph = build_company_refresh_graph(
            runtime=runtime,
            panel_ids=["gatekeepers", "demand_revenue_quality"],
            memo_reconciliation=True,
            monitoring_enabled=True,
            checkpointer=checkpointer,
        )
        initial = graph.invoke(
            {
                "company_id": "ACME",
                "run_id": "run_pause_continue",
                "panel_ids": ["gatekeepers", "demand_revenue_quality"],
            },
            config=checkpoint_config("run_pause_continue"),
        )
        payloads = interrupt_payloads(initial)
        resumed = graph.invoke(
            Command(resume={"action": "continue"}),
            config=checkpoint_config("run_pause_continue"),
        )

    assert payloads and payloads[0]["checkpoint_panel_id"] == "gatekeepers"
    assert payloads[0]["allowed_actions"] == ["stop", "continue"]
    assert "demand_revenue_quality" not in initial.get("panel_results", {})
    assert "demand_revenue_quality" in resumed["panel_results"]
    assert resumed["provisional"] is False
    assert resumed["memo"]["recommendation_summary"] == "memo reconciled"


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


def test_analysis_service_pauses_and_resumes_same_run_id(seeded_acme) -> None:
    service = AnalysisService(seeded_acme)

    paused = service.analyze_company("ACME")
    run_id = paused["run"]["run_id"]

    assert paused["run"]["status"] == "awaiting_continue"
    assert paused["run"]["awaiting_continue"] is True
    assert paused["delta"] is None
    assert "gatekeepers" in paused["panels"]
    assert "demand_revenue_quality" not in paused["panels"]

    resumed = service.continue_run(run_id)

    assert resumed["run"]["run_id"] == run_id
    assert resumed["run"]["status"] == "complete"
    assert resumed["run"]["awaiting_continue"] is False
    assert "demand_revenue_quality" in resumed["panels"]
    assert resumed["delta"] is not None


def test_run_due_coverage_keeps_paused_runs_due_and_queryable(seeded_acme) -> None:
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

    paused = AnalysisService(seeded_acme).analyze_company("ACME")
    resumed = AnalysisService(seeded_acme).continue_run(paused["run"]["run_id"])

    assert resumed["run"]["status"] == "complete"
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")

    assert coverage is not None
    assert coverage.last_run_at is not None
    assert coverage.next_run_at == datetime(2026, 3, 16, 13, 30, tzinfo=UTC)


def test_stopped_run_does_not_advance_coverage_schedule(seeded_acme) -> None:
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

    assert stopped["run"]["status"] == "stopped"
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
    with pytest.raises(
        ValueError,
        match=r"Panel supply_product_operations is not implemented for policy weekly_default\.",
    ):
        AnalysisService(seeded_acme).run_panel("ACME", "supply_product_operations")

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


def test_refresh_company_rejects_full_surface_policy_before_run_creation(seeded_acme) -> None:
    _set_panel_policy(seeded_acme, "ACME", "full_surface")

    with pytest.raises(
        ValueError,
        match=r"Panel supply_product_operations is not implemented for policy full_surface\.",
    ):
        AnalysisService(seeded_acme).refresh_company("ACME")

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


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
    def __init__(self, *, gate_decision: GateDecision) -> None:
        self.context = StubContext()
        self.gate_decision = gate_decision

    def execute_panel(self, panel_id: str) -> dict[str, object]:
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
        return {"claims": [], "verdict": verdict.model_dump(mode="json")}

    def finalize_panel_verdict(self, *, panel_id: str, verdict):
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
