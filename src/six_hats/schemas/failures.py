from __future__ import annotations

from pydantic import BaseModel

from six_hats.schemas.hat_output import ThinkingHatName


class FailureRecord(BaseModel):
    """A node failure. The message is sanitised and never contains prompt content."""

    node: str
    hat: ThinkingHatName | None = None
    error_type: str
    attempts: int = 1
    message: str = ""
