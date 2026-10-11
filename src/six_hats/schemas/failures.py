from __future__ import annotations

from pydantic import BaseModel

from six_hats.schemas.hat_output import HatName


class FailureRecord(BaseModel):
    hat: HatName
    error_type: str
    message: str
    attempts: int = 1
