"""Deterministic rules for hat sequences. The model proposes; this code has the last word.

Rules come from de Bono's text (Penguin edition, chapter 3, "Using the Hats"):
- Blue opens and closes every session (always the case here: Blue-Open and Blue-Close).
- In an assessment, the yellow hat goes before the black hat.
A hat may appear more than once, so each step gets its own key.
"""

from __future__ import annotations

from typing import Any

from six_hats.schemas.framing import Framing
from six_hats.schemas.hat_output import THINKING_HATS, SequenceStep
from six_hats.schemas.presets import CUSTOM, PRESETS, SequenceOverride


def step_key(hat: SequenceStep, earlier: list[SequenceStep]) -> str:
    """ "white" for a hat's first step, "white#2" for its second, and so on."""
    n = earlier.count(hat) + 1
    return hat if n == 1 else f"{hat}#{n}"


def _tidy_blue(seq: list[SequenceStep]) -> list[SequenceStep]:
    """Drop a Blue that is first, last or repeated; Blue already opens and closes the session."""
    tidy: list[SequenceStep] = []
    for step in seq:
        if step == "blue" and (not tidy or tidy[-1] == "blue"):
            continue
        tidy.append(step)
    while tidy and tidy[-1] == "blue":
        tidy.pop()
    return tidy or list(THINKING_HATS)


def apply_sequence_rules(framing: Framing) -> tuple[Framing, bool]:
    """Return the framing with rule violations fixed, and whether anything changed."""
    seq = _tidy_blue(list(framing.sequence))
    if framing.thinking_type == "evaluation" and "yellow" in seq and "black" in seq:
        y, b = seq.index("yellow"), seq.index("black")
        if b < y:
            seq[y], seq[b] = seq[b], seq[y]
    changed = seq != list(framing.sequence)
    return (framing.model_copy(update={"sequence": seq}) if changed else framing), changed


def resolve_order(framing: Framing, override: SequenceOverride | None) -> tuple[Framing, str]:
    """Settle the final order. Returns the framing and how the order was decided:
    "override", "preset", "rules" (the model's own order, adjusted) or "unchanged".

    A caller's override beats Blue-Open. A preset id chosen by Blue-Open is expanded from code,
    so the model cannot alter a preset's order. Anything else is Blue-Open's own sequence
    plus the rules.
    """
    if override is not None and override.parallel:
        update_p: dict[str, Any] = {
            "preset": None,
            "sequence": list(THINKING_HATS),
            "mode": "parallel",
        }
        return framing.model_copy(update=update_p), "override"
    if override is not None:
        name: str
        order: list[SequenceStep]
        if override.preset is not None:
            preset = PRESETS[override.preset]
            name, order = preset.id, list(preset.sequence)
        else:
            name, order = CUSTOM, list(override.sequence or [])
        update: dict[str, Any] = {"preset": name, "sequence": order, "mode": "sequential"}
        return framing.model_copy(update=update), "override"
    if framing.preset in PRESETS:
        preset = PRESETS[framing.preset]
        return (
            framing.model_copy(update={"sequence": list(preset.sequence), "mode": "sequential"}),
            "preset",
        )
    fixed, changed = apply_sequence_rules(framing)
    return fixed, "rules" if changed else "unchanged"
