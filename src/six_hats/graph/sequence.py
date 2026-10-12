"""Deterministic rules for hat sequences. The model proposes; this code has the last word.

Rules come from de Bono's text (Penguin edition, chapter 3, "Using the Hats"):
- Blue opens and closes every session (always the case here: Blue-Open and Blue-Close).
- In an assessment, the yellow hat goes before the black hat.
A hat may appear more than once, so each step gets its own key.
"""

from __future__ import annotations

from six_hats.schemas.framing import Framing
from six_hats.schemas.hat_output import ThinkingHatName


def step_key(hat: ThinkingHatName, earlier: list[ThinkingHatName]) -> str:
    """ "white" for a hat's first step, "white#2" for its second, and so on."""
    n = earlier.count(hat) + 1
    return hat if n == 1 else f"{hat}#{n}"


def apply_sequence_rules(framing: Framing) -> tuple[Framing, bool]:
    """Return the framing with rule violations fixed, and whether anything changed."""
    seq = list(framing.sequence)
    if framing.thinking_type == "evaluation" and "yellow" in seq and "black" in seq:
        y, b = seq.index("yellow"), seq.index("black")
        if b < y:
            seq[y], seq[b] = seq[b], seq[y]
    changed = seq != list(framing.sequence)
    return (framing.model_copy(update={"sequence": seq}) if changed else framing), changed
