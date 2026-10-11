"""Routing is deterministic code over validated state. No model text is ever used as a node name."""

from __future__ import annotations

from six_hats.graph.state import GraphState
from six_hats.schemas.hat_output import THINKING_HATS


def route_after_blue_open(_state: GraphState) -> list[str]:
    """Phase 2 runs every hat in parallel. Phase 3 adds sequential mode here."""
    return list(THINKING_HATS)
