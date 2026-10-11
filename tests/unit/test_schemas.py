import pytest
from pydantic import ValidationError

from six_hats.schemas.failures import FailureRecord
from six_hats.schemas.framing import Framing
from six_hats.schemas.hat_output import HatOutput
from six_hats.schemas.report import FinalReport


def test_hat_output_bounds():
    with pytest.raises(ValidationError):
        HatOutput(hat="white", key_points=["a", "b"])
    with pytest.raises(ValidationError):
        HatOutput(hat="white", key_points=list("abcdefgh"))
    assert HatOutput(hat="white", key_points=["a", "b", "c"]).confidence == "medium"


def test_unknown_hat_rejected():
    with pytest.raises(ValidationError):
        HatOutput(hat="purple", key_points=["a", "b", "c"])


def test_report_degraded():
    assert not FinalReport(summary="s", recommendation="r").degraded
    f = FailureRecord(hat="red", error_type="Timeout", message="m")
    assert FinalReport(summary="s", recommendation="r", failures=[f]).degraded


def test_framing_sequence_limits():
    with pytest.raises(ValidationError):
        Framing(problem_statement="p", mode="evaluate_idea", sequence=[])
