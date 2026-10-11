from __future__ import annotations

from typing import Annotated, Final, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

ThinkingHatName = Literal["white", "red", "green", "yellow", "black"]
HatName = Literal["white", "red", "green", "yellow", "black", "blue"]

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
