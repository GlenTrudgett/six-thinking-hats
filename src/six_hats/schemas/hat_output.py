from __future__ import annotations

from typing import Annotated, Final, Literal

from pydantic import BaseModel, Field, StringConstraints

ThinkingHatName = Literal["white", "red", "green", "yellow", "black"]
HatName = Literal["white", "red", "green", "yellow", "black", "blue"]

# Order is stable and used for display; routing treats it as an allow-list.
THINKING_HATS: Final[tuple[ThinkingHatName, ...]] = ("white", "red", "green", "yellow", "black")

Point = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class HatOutput(BaseModel):
    hat: ThinkingHatName
    key_points: list[Point] = Field(min_length=3, max_length=7)
    assumptions: list[Point] = Field(default_factory=list, max_length=7)
    open_questions: list[Point] = Field(default_factory=list, max_length=7)
    confidence: Literal["low", "medium", "high"] | None = None
