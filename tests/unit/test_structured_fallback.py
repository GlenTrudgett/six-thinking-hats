import pytest

from six_hats.llm.structured import StructuredOutputError, ainvoke_structured, extract_json
from six_hats.schemas.hat_output import HatOutput
from tests.support.fakes import make_fake
from tests.support.json_fake import HttpError, no_structured

GOOD_JSON = '{"hat": "white", "key_points": ["a", "b", "c"]}'


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert extract_json('Sure! Here you go: {"a": {"b": 2}} Hope that helps.') == '{"a": {"b": 2}}'
    with pytest.raises(ValueError, match="no JSON"):
        extract_json("no json here")


@pytest.mark.parametrize("error", [NotImplementedError(), HttpError(400), HttpError(422)])
async def test_unsupported_native_falls_back_to_json_mode(error):
    model = no_structured(f"```json\n{GOOD_JSON}\n```", error=error)
    out = await ainvoke_structured(model, HatOutput, "system", "user")
    assert out.hat == "white" and len(out.key_points) == 3


async def test_json_mode_gets_one_repair_retry():
    model = no_structured("not json at all", GOOD_JSON)
    assert (await ainvoke_structured(model, HatOutput, "s", "u")).hat == "white"


async def test_json_mode_gives_up_after_the_retry():
    model = no_structured("nope", '{"hat": "white", "key_points": []}', GOOD_JSON)
    with pytest.raises(StructuredOutputError):
        await ainvoke_structured(model, HatOutput, "s", "u")


@pytest.mark.parametrize("status", [401, 403, 429, 500])
async def test_auth_and_server_errors_are_not_swallowed(status):
    model = no_structured(GOOD_JSON, error=HttpError(status))
    with pytest.raises(HttpError):
        await ainvoke_structured(model, HatOutput, "s", "u")


async def test_unrelated_exceptions_propagate():
    model = no_structured(GOOD_JSON, error=ConnectionError("refused"))
    with pytest.raises(ConnectionError):
        await ainvoke_structured(model, HatOutput, "s", "u")


async def test_no_supported_method_is_a_typed_error():
    model = no_structured(GOOD_JSON)
    with pytest.raises(StructuredOutputError, match="no supported"):
        await ainvoke_structured(model, HatOutput, "s", "u", methods=("native",))


async def test_native_success_never_touches_json_mode():
    good = HatOutput(hat="red", key_points=["a", "b", "c"])
    model = make_fake(good)
    assert await ainvoke_structured(model, HatOutput, "s", "u") == good
    assert model.calls == 1


async def test_json_mode_prompt_carries_schema_and_instruction():
    seen = []

    class Spy(type(no_structured())):  # type: ignore[misc]
        async def _agenerate(self, messages, *a, **k):
            seen.extend(m.content for m in messages)
            return await super()._agenerate(messages, *a, **k)

    model = Spy(
        messages=iter(
            [
                __import__("langchain_core.messages", fromlist=["AIMessage"]).AIMessage(
                    content=GOOD_JSON
                )
            ]
        ),
        error=NotImplementedError(),
    )
    await ainvoke_structured(model, HatOutput, "SYSTEM", "USER")
    assert "SYSTEM" in seen[0] and "JSON Schema" in seen[0] and "key_points" in seen[0]
    assert seen[1] == "USER"


async def test_config_value_error_is_a_config_error_not_a_retry():
    from six_hats.llm.factory import ConfigError

    model = no_structured(GOOD_JSON, error=ValueError("temperature is not supported"))
    with pytest.raises(ConfigError, match="temperature"):
        await ainvoke_structured(model, HatOutput, "s", "u")
