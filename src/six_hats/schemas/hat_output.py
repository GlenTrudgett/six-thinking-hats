from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HatName = Literal["white", "red", "green", "yellow", "black", "blue"]


class HatOutput(BaseModel):
    hat: HatName
    key_points: list[str] = Field(min_length=3, max_length=7)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
