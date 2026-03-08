from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from langgraph.graph import END, StateGraph

from ai_investing.domain.models import GatekeeperVerdict, PanelVerdict

if TYPE_CHECKING:
    from ai_investing.application.services import RefreshRuntime


class PanelState(TypedDict, total=False):
    claims: list[dict[str, Any]]
    verdict: dict[str, Any]


class MemoState(TypedDict, total=False):
    memo: dict[str, Any]


class DeltaState(TypedDict, total=False):
    delta: dict[str, Any]


def build_panel_lead_subgraph(runtime: RefreshRuntime, panel_id: str):
    def finalize(state: PanelState) -> PanelState:
        verdict_payload = state["verdict"]
        verdict = (
            GatekeeperVerdict.model_validate(verdict_payload)
            if "gate_decision" in verdict_payload
            else PanelVerdict.model_validate(verdict_payload)
        )
        final_verdict = runtime.finalize_panel_verdict(panel_id=panel_id, verdict=verdict)
        return {"verdict": final_verdict.model_dump(mode="json")}

    graph = StateGraph(PanelState)
    graph.add_node("finalize", finalize)
    graph.set_entry_point("finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def build_debate_subgraph(runtime: RefreshRuntime, panel_id: str):
    panel = runtime.context.get_panel(panel_id)
    lead_graph = build_panel_lead_subgraph(runtime, panel_id)

    def specialist_node(_state: PanelState) -> PanelState:
        result = runtime.execute_panel(panel.id)
        return {"claims": result["claims"], "verdict": result["verdict"]}

    def lead_node(state: PanelState) -> PanelState:
        return lead_graph.invoke(state)

    graph = StateGraph(PanelState)
    graph.add_node("specialists_and_judge", specialist_node)
    graph.add_node("lead", lead_node)
    graph.set_entry_point("specialists_and_judge")
    graph.add_edge("specialists_and_judge", "lead")
    graph.add_edge("lead", END)
    return graph.compile()


def build_gatekeeper_subgraph(runtime: RefreshRuntime, panel_id: str):
    return build_debate_subgraph(runtime, panel_id)


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


def build_ic_synthesis_graph(runtime: RefreshRuntime):
    def synthesize(state: MemoState) -> MemoState:
        memo = runtime.reconcile_ic_memo()
        return {"memo": memo.model_dump(mode="json")}

    graph = StateGraph(MemoState)
    graph.add_node("synthesize", synthesize)
    graph.set_entry_point("synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()
