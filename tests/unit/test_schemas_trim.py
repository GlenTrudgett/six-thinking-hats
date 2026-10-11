import pytest
from pydantic import ValidationError

from six_hats.schemas.hat_output import HatOutput
from six_hats.schemas.report import BlueCloseOutput


def test_overlong_lists_are_trimmed_not_rejected():
    out = BlueCloseOutput(
        framing_summary="f",
        conclusions=[f"c{i}" for i in range(9)],
        open_questions=[f"q{i}" for i in range(8)],
    )
    assert len(out.conclusions) == 7 and out.open_questions[-1] == "q6"
    hat = HatOutput(hat="white", key_points=[str(i) for i in range(10)])
    assert len(hat.key_points) == 7


def test_too_few_points_still_rejected():
    with pytest.raises(ValidationError):
        HatOutput(hat="white", key_points=["a", "b"])
