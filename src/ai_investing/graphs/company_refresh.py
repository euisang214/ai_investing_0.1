from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph

from ai_investing.graphs.state import RefreshState
from ai_investing.graphs.subgraphs import (
    build_gatekeeper_checkpoint,
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
    checkpointer: object | None = None,
):
    graph = StateGraph(RefreshState)
    panel_terminal_nodes: list[tuple[str, str, str]] = []
    for panel_id in panel_ids:
        panel = runtime.context.get_panel(panel_id)
        panel_builder = get_panel_subgraph_builder(panel.subgraph)
        panel_node = f"panel__{panel_id}"
        memo_node = f"memo__{panel_id}"
        graph.add_node(panel_node, panel_builder(runtime, panel_id))
        if memo_reconciliation:
            graph.add_node(memo_node, build_memo_update_subgraph(runtime, panel_id))
            graph.add_edge(panel_node, memo_node)
        terminal_node = memo_node if memo_reconciliation else panel_node
        panel_terminal_nodes.append((panel_id, panel_node, terminal_node))

    monitoring_node = "monitoring"
    ic_node = "ic_synthesis"
    monitoring_graph = (
        build_monitoring_diff_subgraph(runtime)
        if monitoring_enabled
        else build_monitoring_skip_subgraph(runtime)
    )
    graph.add_node(monitoring_node, monitoring_graph)
    graph.add_node(ic_node, build_ic_synthesis_graph(runtime))

    if not panel_terminal_nodes:
        graph.set_entry_point(monitoring_node)
    else:
        graph.set_entry_point(panel_terminal_nodes[0][1])
        for index, (panel_id, _panel_node, terminal_node) in enumerate(panel_terminal_nodes):
            next_panel_node = (
                panel_terminal_nodes[index + 1][1]
                if index + 1 < len(panel_terminal_nodes)
                else monitoring_node
            )
            if panel_id == "gatekeepers":
                checkpoint_node = f"checkpoint__{panel_id}"
                graph.add_node(
                    checkpoint_node,
                    build_gatekeeper_checkpoint(
                        runtime,
                        continue_to=next_panel_node,
                        stop_to=monitoring_node,
                    ),
                )
                graph.add_edge(terminal_node, checkpoint_node)
            else:
                graph.add_edge(terminal_node, next_panel_node)
    graph.add_edge(monitoring_node, ic_node)
    graph.add_edge(ic_node, END)
    compile_kwargs: dict[str, object] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    return graph.compile(**compile_kwargs)
