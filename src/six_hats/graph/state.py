from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from six_hats.schemas.failures import FailureRecord
from six_hats.schemas.framing import Framing
from six_hats.schemas.hat_output import HatOutput
from six_hats.schemas.presets import SequenceOverride
from six_hats.schemas.report import FinalReport


def merge_outputs(left: dict[str, HatOutput], right: dict[str, HatOutput]) -> dict[str, HatOutput]:
    """Merge by key so parallel hats can write concurrently."""
    return {**left, **right}


class GraphState(TypedDict, total=False):
    run_id: str
    question: str
    override: SequenceOverride | None
    framing: Framing
    outputs: Annotated[dict[str, HatOutput], merge_outputs]
    failures: Annotated[list[FailureRecord], operator.add]
    report: FinalReport
