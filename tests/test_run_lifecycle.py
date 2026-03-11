from __future__ import annotations

from ai_investing.domain.enums import GateDecision, RunContinueAction, RunKind, RunStatus
from ai_investing.domain.models import RunCheckpoint, RunRecord
from ai_investing.persistence.repositories import Repository


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
