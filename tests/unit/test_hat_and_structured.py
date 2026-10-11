import pytest
from pydantic import ValidationError

from six_hats.hats.base import load_prompt, run_hat
from six_hats.llm.structured import StructuredOutputError, ainvoke_structured
from six_hats.schemas.hat_output import HatOutput
from tests.support.fakes import make_fake

GOOD = HatOutput(hat="red", key_points=["a", "b", "c"])


def _bad():
    try:
        HatOutput(hat="white", key_points=[])
    except ValidationError as e:
        return e


async def test_run_hat_sets_hat_name():
    out = await run_hat("white", make_fake(GOOD), "request")
    assert out.hat == "white"


async def test_structured_retries_once_then_succeeds():
    model = make_fake(_bad(), GOOD)
    assert (await ainvoke_structured(model, HatOutput, "s", "u")) == GOOD
    assert model.calls == 2


async def test_structured_gives_up_after_one_retry():
    model = make_fake(_bad(), _bad(), GOOD)
    with pytest.raises(StructuredOutputError):
        await ainvoke_structured(model, HatOutput, "s", "u")
    assert model.calls == 2


def test_white_prompt_treats_request_as_data():
    assert "never instructions" in load_prompt("white")
