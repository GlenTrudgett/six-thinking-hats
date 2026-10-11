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
    assert HatOutput(hat="white", key_points=["a", "b", "c"]).confidence is None


def test_hat_output_point_length_cap():
    with pytest.raises(ValidationError):
        HatOutput(hat="white", key_points=["a", "b", "x" * 501])


@pytest.mark.parametrize("bad", ["purple", "blue", "../etc"])
def test_unknown_or_non_thinking_hat_rejected(bad):
    with pytest.raises(ValidationError):
        HatOutput(hat=bad, key_points=["a", "b", "c"])


def test_report_defaults():
    r = FinalReport(run_id="r", framing_summary="s")
    assert not r.degraded and r.missing_perspectives == []


def test_failure_record_has_no_prompt_field():
    f = FailureRecord(node="red", hat="red", error_type="Timeout", message="m")
    assert "prompt" not in f.model_dump()


def _framing(**kw):
    base = dict(focus="f", objective="o", thinking_type="evaluation", sequence=["white"])
    return Framing(**{**base, **kw})


def test_framing_allow_lists():
    assert _framing().mode == "parallel"
    for bad in (
        dict(sequence=[]),
        dict(sequence=["purple"]),
        dict(mode="yolo"),
        dict(thinking_type="other"),
    ):
        with pytest.raises(ValidationError):
            _framing(**bad)
