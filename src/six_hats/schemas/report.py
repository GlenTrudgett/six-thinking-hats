from __future__ import annotations

from pydantic import BaseModel, Field

from six_hats.schemas.failures import FailureRecord
from six_hats.schemas.hat_output import HatOutput


class FinalReport(BaseModel):
    summary: str
    recommendation: str
    hats: list[HatOutput] = Field(default_factory=list)
    failures: list[FailureRecord] = Field(default_factory=list)

    @property
    def degraded(self) -> bool:
        return bool(self.failures)
