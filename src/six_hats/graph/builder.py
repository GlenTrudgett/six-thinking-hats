from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from six_hats.graph.nodes import (
    ModelResolver,
    make_blue_close,
    make_blue_open,
    make_hat,
    make_intake,
)
from six_hats.graph.routing import route_after_blue_open
from six_hats.graph.state import GraphState
from six_hats.schemas.hat_output import THINKING_HATS


def build_graph(resolve: ModelResolver, *, max_question_chars: int = 4000) -> CompiledStateGraph:  # type: ignore[type-arg]
    """intake -> blue_open -> (five hats in parallel) -> blue_close.

    Each node uses static edges or conditional routing, never both. No checkpointer is attached.
    """
    graph = StateGraph(GraphState)
    graph.add_node("intake", make_intake(max_question_chars))
    graph.add_node("blue_open", make_blue_open(resolve))
    for hat in THINKING_HATS:
        graph.add_node(hat, make_hat(hat, resolve))
    graph.add_node("blue_close", make_blue_close(resolve))

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "blue_open")
    graph.add_conditional_edges("blue_open", route_after_blue_open, list(THINKING_HATS))
    for hat in THINKING_HATS:
        graph.add_edge(hat, "blue_close")
    graph.add_edge("blue_close", END)
    return graph.compile()
