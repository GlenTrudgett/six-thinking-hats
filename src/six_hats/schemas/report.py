from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from six_hats.schemas.failures import FailureRecord
from six_hats.schemas.hat_output import ThinkingHatName, trim_to

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)]


class HatSummary(BaseModel):
    hat: ThinkingHatName
    summary: Text


class BlueCloseOutput(BaseModel):
    """What Blue-Close (the LLM) writes. Metadata is added in code, never by the model."""

    framing_summary: Text
    hat_summaries: Annotated[list[HatSummary], trim_to(5)] = Field(
        default_factory=list, max_length=5
    )
    conclusions: Annotated[list[Text], trim_to(7)] = Field(min_length=1, max_length=7)
    agreements: Annotated[list[Text], trim_to(7)] = Field(default_factory=list, max_length=7)
    tensions: Annotated[list[Text], trim_to(7)] = Field(default_factory=list, max_length=7)
    recommended_next_steps: Annotated[list[Text], trim_to(7)] = Field(
        default_factory=list, max_length=7
    )
    open_questions: Annotated[list[Text], trim_to(7)] = Field(default_factory=list, max_length=7)


class FinalReport(BaseModel):
    run_id: str
    framing_summary: str
    hat_summaries: list[HatSummary] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    agreements: list[str] = Field(default_factory=list)
    tensions: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    missing_perspectives: list[ThinkingHatName] = Field(default_factory=list)
    mode: Literal["parallel", "sequential"] = "parallel"
    sequence: list[ThinkingHatName] = Field(default_factory=list)
    preset: str | None = None
    preset_source: Literal["book", "unverified"] | None = None
    degraded: bool = False
    failures: list[FailureRecord] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
