from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph

from ai_investing.graphs.state import RefreshState
from ai_investing.graphs.subgraphs import (
    build_ic_synthesis_graph,
    build_memo_update_subgraph,
    build_monitoring_diff_subgraph,
    build_monitoring_skip_subgraph,
    get_panel_subgraph_builder,
)

if TYPE_CHECKING:
    from ai_investing.application.services import RefreshRuntime


def build_company_refresh_graph(
    runtime: RefreshRuntime,
    panel_ids: list[str],
    *,
    memo_reconciliation: bool,
    monitoring_enabled: bool,
):
    graph = StateGraph(RefreshState)
    previous_node: str | None = None
    for panel_id in panel_ids:
        panel = runtime.context.get_panel(panel_id)
        panel_builder = get_panel_subgraph_builder(panel.subgraph)
        panel_node = f"panel__{panel_id}"
        memo_node = f"memo__{panel_id}"
        graph.add_node(panel_node, panel_builder(runtime, panel_id))
        if previous_node is None:
            graph.set_entry_point(panel_node)
        else:
            graph.add_edge(previous_node, panel_node)
        if memo_reconciliation:
            graph.add_node(memo_node, build_memo_update_subgraph(runtime, panel_id))
            graph.add_edge(panel_node, memo_node)
            previous_node = memo_node
        else:
            previous_node = panel_node

    monitoring_node = "monitoring"
    ic_node = "ic_synthesis"
    monitoring_graph = (
        build_monitoring_diff_subgraph(runtime)
        if monitoring_enabled
        else build_monitoring_skip_subgraph(runtime)
    )
    graph.add_node(monitoring_node, monitoring_graph)
    graph.add_node(ic_node, build_ic_synthesis_graph(runtime))

    if previous_node is None:
        graph.set_entry_point(monitoring_node)
    else:
        graph.add_edge(previous_node, monitoring_node)
    graph.add_edge(monitoring_node, ic_node)
    graph.add_edge(ic_node, END)
    return graph.compile()
