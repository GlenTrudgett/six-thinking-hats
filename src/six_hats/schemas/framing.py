from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from six_hats.schemas.hat_output import ThinkingHatName
from six_hats.schemas.presets import MAX_SEQUENCE_STEPS, PresetId

Sentence = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class Framing(BaseModel):
    """Blue-Open's framing. Mode and sequence are validated against allow-lists."""

    focus: Sentence
    objective: Sentence
    thinking_type: Literal["new_idea", "evaluation", "problem"]
    mode: Literal["parallel", "sequential"] = "parallel"
    sequence: list[ThinkingHatName] = Field(min_length=1, max_length=MAX_SEQUENCE_STEPS)
    preset: PresetId | Literal["custom"] | None = None
    rationale: Annotated[str, StringConstraints(max_length=800)] = ""
