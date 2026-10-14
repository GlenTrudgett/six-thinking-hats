"""The Blue Hat's mid-sequence checkpoint. It reports and focuses; it cannot change the sequence."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from six_hats.schemas.hat_output import Point, ThinkingHatName, trim_to

Focus = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class BlueCheckpoint(BaseModel):
    """What the Blue Hat writes between two hats."""

    progress: Annotated[list[Point], trim_to(3)] = Field(min_length=1, max_length=3)
    gaps: Annotated[list[Point], trim_to(3)] = Field(default_factory=list, max_length=3)
    next_focus: Focus


class CheckpointRecord(BaseModel):
    """A checkpoint plus where it happened. `after` is the hat whose output it follows."""

    after: ThinkingHatName
    checkpoint: BlueCheckpoint
