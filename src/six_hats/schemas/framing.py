from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from six_hats.schemas.hat_output import HatName


class Framing(BaseModel):
    problem_statement: str
    mode: Literal["evaluate_idea", "generate_ideas", "solve_problem"]
    sequence: list[HatName] = Field(min_length=1, max_length=5)
    rationale: str = ""
