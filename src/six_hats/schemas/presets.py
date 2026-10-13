"""Named hat orders for common kinds of thinking.

Blue opens and closes every session, so a preset lists only the five coloured hats. Code, not the
model, turns a preset id into an order. `source` records where an order came from:
- "book": checked against de Bono's *Six Thinking Hats*.
- "advanced": a more advanced sequence taken from a secondary summary, not the book text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from six_hats.schemas.hat_output import ThinkingHatName

PresetId = Literal[
    "initial_ideas",
    "choosing_between_alternatives",
    "identifying_solutions",
    "quick_feedback",
    "process_improvement",
    "problem_solving",
    "performance_review",
]
MAX_SEQUENCE_STEPS = 8
Source = Literal["book", "advanced"]


@dataclass(frozen=True)
class Preset:
    id: PresetId
    title: str
    use_when: str
    sequence: tuple[ThinkingHatName, ...]
    source: Source = "advanced"


PRESETS: dict[str, Preset] = {
    p.id: p
    for p in (
        Preset(
            "initial_ideas",
            "Initial ideas",
            "Generating a first set of ideas or a brainstorm.",
            ("white", "green"),
        ),
        Preset(
            "choosing_between_alternatives",
            "Choosing between alternatives",
            "Comparing options and picking one.",
            ("white", "green", "yellow", "black", "red"),
        ),
        Preset(
            "identifying_solutions",
            "Identifying solutions",
            "A problem is understood and a way out is needed.",
            ("white", "black", "green"),
        ),
        Preset(
            "quick_feedback",
            "Quick feedback",
            "A fast reaction to a proposal: its weak points and how to fix them.",
            ("black", "green"),
        ),
        Preset(
            "process_improvement",
            "Process improvement",
            "Improving how something is done. White appears twice: the second turn "
            "gathers other people's views.",
            ("white", "white", "yellow", "black", "green", "red"),
        ),
        Preset(
            "problem_solving",
            "Problem solving",
            "Working through a defined problem from facts to a refined solution.",
            ("white", "green", "red", "yellow", "black", "green"),
        ),
        Preset(
            "performance_review",
            "Performance review",
            "Looking back at how something went.",
            ("red", "white", "yellow", "black", "green", "red"),
        ),
    )
}

CUSTOM = "custom"


def preset_ids() -> tuple[str, ...]:
    return tuple(PRESETS)


def describe_presets() -> str:
    """The preset list as shown to Blue-Open."""
    return "\n".join(
        f"- {p.id}: {p.use_when} Order: {', '.join(p.sequence)}." for p in PRESETS.values()
    )


class SequenceOverride(BaseModel):
    """A caller's choice of order that replaces Blue-Open's. Exactly one of the two fields."""

    preset: PresetId | None = None
    sequence: list[ThinkingHatName] | None = Field(
        default=None, min_length=1, max_length=MAX_SEQUENCE_STEPS
    )

    @model_validator(mode="after")
    def _exactly_one(self) -> SequenceOverride:
        if (self.preset is None) == (self.sequence is None):
            raise ValueError("give either a preset or a sequence, not both or neither")
        return self
