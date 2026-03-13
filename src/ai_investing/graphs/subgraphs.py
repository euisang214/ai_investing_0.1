from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt

from ai_investing.domain.enums import GateDecision, RunContinueAction
from ai_investing.domain.models import GatekeeperVerdict, PanelVerdict
from ai_investing.graphs.state import RefreshState

if TYPE_CHECKING:
    from ai_investing.application.services import RefreshRuntime


class MemoState(TypedDict, total=False):
    memo: dict[str, Any]


class DeltaState(TypedDict, total=False):
    delta: dict[str, Any]


def get_panel_subgraph_builder(subgraph_id: str):
    builders = {
        "debate": build_debate_subgraph,
        "gatekeeper": build_gatekeeper_subgraph,
    }
    try:
        return builders[subgraph_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported panel subgraph: {subgraph_id}") from exc


def build_panel_lead_subgraph(runtime: RefreshRuntime, panel_id: str):
    def finalize(state: RefreshState) -> RefreshState:
        skip_payload = state.get("skip")
        if skip_payload is not None:
            panel_results = dict(state.get("panel_results", {}))
            panel_results[panel_id] = {
                "claims": state.get("claims", []),
                "skip": skip_payload,
            }
            return {
                "panel_results": panel_results,
                "skip": skip_payload,
            }
        verdict_payload = state["verdict"]
        verdict = (
            GatekeeperVerdict.model_validate(verdict_payload)
            if "gate_decision" in verdict_payload
            else PanelVerdict.model_validate(verdict_payload)
        )
        support_payload = state.get("support")
        final_verdict = runtime.finalize_panel_verdict(
            panel_id=panel_id,
            verdict=verdict,
            support_payload=support_payload,
        )
        panel_results = dict(state.get("panel_results", {}))
        panel_results[panel_id] = {
            "claims": state.get("claims", []),
            "verdict": final_verdict.model_dump(mode="json"),
        }
        return {
            "panel_results": panel_results,
            "verdict": final_verdict.model_dump(mode="json"),
        }
    return finalize


def build_debate_subgraph(runtime: RefreshRuntime, panel_id: str):
    panel = runtime.context.get_panel(panel_id)
    lead_node = build_panel_lead_subgraph(runtime, panel_id)

    def specialist_node(_state: RefreshState) -> RefreshState:
        result = runtime.execute_panel(panel.id)
        state: RefreshState = {
            "claims": result.get("claims", []),
            "support": result.get("support"),
        }
        if "verdict" in result:
            state["verdict"] = result["verdict"]
        if "skip" in result:
            state["skip"] = result["skip"]
        return state

    graph = StateGraph(RefreshState)
    graph.add_node("specialists_and_judge", specialist_node)
    graph.add_node("lead", lead_node)
    graph.set_entry_point("specialists_and_judge")
    graph.add_edge("specialists_and_judge", "lead")
    graph.add_edge("lead", END)
    return graph.compile()


def build_gatekeeper_subgraph(runtime: RefreshRuntime, panel_id: str):
    return build_debate_subgraph(runtime, panel_id)


def build_gatekeeper_checkpoint(
    runtime: RefreshRuntime,
    *,
    continue_to: str,
    stop_to: str,
):
    def checkpoint(state: RefreshState) -> Command[str]:
        gatekeeper_verdict = _gatekeeper_verdict_from_state(state, runtime=runtime)
        has_downstream_panels = continue_to != stop_to
        if gatekeeper_verdict.gate_decision in {GateDecision.PASS, GateDecision.REVIEW}:
            update = runtime.auto_continue_gatekeeper(
                gatekeeper=gatekeeper_verdict,
                has_downstream_panels=has_downstream_panels,
            )
            return Command(update=update, goto=continue_to)
        checkpoint_payload = runtime.prepare_gatekeeper_checkpoint(
            gatekeeper=gatekeeper_verdict,
            has_downstream_panels=has_downstream_panels,
        )
        resume_value = interrupt(checkpoint_payload.model_dump(mode="json"))
        action = _coerce_resume_action(resume_value)
        update = runtime.resolve_gatekeeper_action(
            action=action,
            gatekeeper=gatekeeper_verdict,
            has_downstream_panels=has_downstream_panels,
        )
        target = stop_to if action == RunContinueAction.STOP else continue_to
        return Command(update=update, goto=target)

    return checkpoint


def build_memo_update_subgraph(runtime: RefreshRuntime, panel_id: str):
    def update(_state: MemoState) -> MemoState:
        result = runtime.update_memo_for_panel(panel_id)
        return {"memo": result["memo"]}

    graph = StateGraph(MemoState)
    graph.add_node("update", update)
    graph.set_entry_point("update")
    graph.add_edge("update", END)
    return graph.compile()


def build_monitoring_diff_subgraph(runtime: RefreshRuntime):
    def compute(_state: DeltaState) -> DeltaState:
        delta = runtime.compute_monitoring_delta()
        return {"delta": delta.model_dump(mode="json")}

    graph = StateGraph(DeltaState)
    graph.add_node("compute", compute)
    graph.set_entry_point("compute")
    graph.add_edge("compute", END)
    return graph.compile()


def build_monitoring_skip_subgraph(runtime: RefreshRuntime):
    def skip(_state: DeltaState) -> DeltaState:
        delta = runtime.skip_monitoring_delta()
        return {"delta": delta.model_dump(mode="json")}

    graph = StateGraph(DeltaState)
    graph.add_node("skip", skip)
    graph.set_entry_point("skip")
    graph.add_edge("skip", END)
    return graph.compile()


def build_ic_synthesis_graph(runtime: RefreshRuntime):
    def synthesize(state: MemoState) -> MemoState:
        memo = runtime.reconcile_ic_memo()
        return {"memo": memo.model_dump(mode="json")}

    graph = StateGraph(MemoState)
    graph.add_node("synthesize", synthesize)
    graph.set_entry_point("synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


def _gatekeeper_verdict_from_state(
    state: RefreshState,
    *,
    runtime: RefreshRuntime | None = None,
) -> GatekeeperVerdict:
    panel_results = state.get("panel_results", {})
    gatekeeper_result = panel_results.get("gatekeepers", {})
    verdict_payload = gatekeeper_result.get("verdict") or state.get("verdict")
    if verdict_payload is None and runtime is not None:
        verdict = runtime.current_verdicts.get("gatekeepers")
        if verdict is not None:
            return GatekeeperVerdict.model_validate(verdict.model_dump(mode="json"))
        with runtime.context.database.session() as session:
            from ai_investing.persistence.repositories import Repository

            repository = Repository(session)
            persisted = next(
                (
                    item
                    for item in repository.list_panel_verdicts(
                        runtime.company_profile.company_id,
                        run_id=runtime.run.run_id,
                    )
                    if item.panel_id == "gatekeepers"
                ),
                None,
            )
        if persisted is not None:
            return GatekeeperVerdict.model_validate(persisted.model_dump(mode="json"))
    if verdict_payload is None:
        raise ValueError("Gatekeeper checkpoint requires a gatekeeper verdict in graph state.")
    return GatekeeperVerdict.model_validate(verdict_payload)


def _coerce_resume_action(value: object) -> RunContinueAction:
    if isinstance(value, RunContinueAction):
        return value
    if isinstance(value, str):
        return RunContinueAction(value)
    if isinstance(value, dict) and "action" in value:
        return RunContinueAction(str(value["action"]))
    raise ValueError(f"Unsupported gatekeeper resume payload: {value!r}")
