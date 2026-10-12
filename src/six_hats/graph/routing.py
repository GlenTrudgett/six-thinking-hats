"""Routing is deterministic code over validated state. No model text is ever used as a node name."""

from __future__ import annotations

from six_hats.graph.state import GraphState
from six_hats.schemas.hat_output import THINKING_HATS


def route_after_blue_open(state: GraphState) -> list[str]:
    """Parallel mode fans out to the five hats; sequential mode runs one node that walks it."""
    framing = state.get("framing")
    if getattr(framing, "mode", None) == "sequential":
        return ["sequential"]
    return list(THINKING_HATS)
