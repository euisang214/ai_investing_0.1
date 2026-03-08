from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any

from langgraph.graph import END, StateGraph

from ai_investing.graphs.state import RefreshState
from ai_investing.graphs.subgraphs import (
    build_debate_subgraph,
    build_gatekeeper_subgraph,
    build_ic_synthesis_graph,
    build_memo_update_subgraph,
    build_monitoring_diff_subgraph,
)

if TYPE_CHECKING:
    from ai_investing.application.services import RefreshRuntime


def _panel_runner(runtime: RefreshRuntime, panel_id: str, state: RefreshState) -> RefreshState:
    panel = runtime.context.get_panel(panel_id)
    subgraph = (
        build_gatekeeper_subgraph(runtime, panel_id)
        if panel.subgraph == "gatekeeper"
        else build_debate_subgraph(runtime, panel_id)
    )
    result = subgraph.invoke({})
    panel_results = dict(state.get("panel_results", {}))
    panel_results[panel_id] = result
    return {"panel_results": panel_results}


def _memo_runner(runtime: RefreshRuntime, panel_id: str, _state: RefreshState) -> RefreshState:
    memo_graph = build_memo_update_subgraph(runtime, panel_id)
    result = memo_graph.invoke({})
    return {"memo": result["memo"]}


def _monitoring_runner(runtime: RefreshRuntime, _state: RefreshState) -> RefreshState:
    delta_graph = build_monitoring_diff_subgraph(runtime)
    result = delta_graph.invoke({})
    return {"delta": result["delta"]}


def _ic_runner(runtime: RefreshRuntime, _state: RefreshState) -> RefreshState:
    ic_graph = build_ic_synthesis_graph(runtime)
    result = ic_graph.invoke({})
    return {"memo": result["memo"]}


def build_company_refresh_graph(runtime: RefreshRuntime, panel_ids: list[str]):
    graph = StateGraph(RefreshState)
    previous_node: str | None = None
    for panel_id in panel_ids:
        panel_node = f"panel__{panel_id}"
        memo_node = f"memo__{panel_id}"
        graph.add_node(panel_node, partial(_panel_runner, runtime, panel_id))
        graph.add_node(memo_node, partial(_memo_runner, runtime, panel_id))
        if previous_node is None:
            graph.set_entry_point(panel_node)
        else:
            graph.add_edge(previous_node, panel_node)
        graph.add_edge(panel_node, memo_node)
        previous_node = memo_node

    monitoring_node = "monitoring"
    ic_node = "ic_synthesis"
    graph.add_node(monitoring_node, partial(_monitoring_runner, runtime))
    graph.add_node(ic_node, partial(_ic_runner, runtime))

    if previous_node is None:
        graph.set_entry_point(monitoring_node)
    else:
        graph.add_edge(previous_node, monitoring_node)
    graph.add_edge(monitoring_node, ic_node)
    graph.add_edge(ic_node, END)
    return graph.compile()
