from __future__ import annotations

from itertools import pairwise
from typing import Annotated, Final, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

ThinkingHatName = Literal["white", "red", "green", "yellow", "black"]
HatName = Literal["white", "red", "green", "yellow", "black", "blue"]

# A step in a sequence: one of the five coloured hats, or "blue" for a mid-sequence checkpoint.
SequenceStep = HatName

# Order is stable and used for display; routing treats it as an allow-list.
THINKING_HATS: Final[tuple[ThinkingHatName, ...]] = ("white", "red", "green", "yellow", "black")

Point = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


def trim_to(limit: int) -> BeforeValidator:
    """Keep the first `limit` items of an over-long list instead of rejecting the reply.

    Models list items in order of importance, so dropping the tail is safe and avoids a
    wasted retry. Too-short lists and wrong types still fail validation.
    """

    def _trim(value: object) -> object:
        return value[:limit] if isinstance(value, list) else value

    return BeforeValidator(_trim)


class HatOutput(BaseModel):
    hat: ThinkingHatName
    key_points: Annotated[list[Point], trim_to(7)] = Field(min_length=3, max_length=7)
    assumptions: Annotated[list[Point], trim_to(7)] = Field(default_factory=list, max_length=7)
    open_questions: Annotated[list[Point], trim_to(7)] = Field(default_factory=list, max_length=7)
    confidence: Literal["low", "medium", "high"] | None = None


def blue_step_problem(steps: list[SequenceStep] | tuple[SequenceStep, ...]) -> str | None:
    """Why a sequence's Blue steps are not allowed, or None. Blue already opens and closes every
    run, so an inner Blue may not be first, last, or next to another Blue."""
    if not steps or "blue" not in steps:
        return None
    if steps[0] == "blue" or steps[-1] == "blue":
        return "blue cannot be the first or last step: Blue already opens and closes the session"
    if any(a == "blue" and b == "blue" for a, b in pairwise(steps)):
        return "blue cannot follow blue"
    if all(s == "blue" for s in steps):
        return "a sequence needs at least one coloured hat"
    return None
