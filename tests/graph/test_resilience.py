"""Phase 4a: a failing node degrades the run instead of sinking it."""

import asyncio

import pytest

from six_hats.graph.resilience import AllHatsFailedError, Limits, is_transient, run_guarded
from six_hats.graph.runner import run_workflow
from six_hats.llm.factory import ConfigError
from six_hats.reporting.render import render_markdown
from tests.support.hats_fake import default_framing, default_response, make_hats_fake
from tests.support.json_fake import HttpError

Q = "Should we adopt a four-day work week?"
FAST = Limits(node_timeout_seconds=1, node_retries=1, retry_backoff_seconds=0)


def _fail(kind_or_hat, error):
    def respond(kind, hat, messages):
        if kind_or_hat in (kind, hat):
            return error
        return default_response(kind, hat, messages)

    return respond


async def test_one_failed_hat_gives_a_degraded_report():
    model = make_hats_fake(_fail("black", RuntimeError("boom")))
    report = await run_workflow(Q, lambda _n: model, run_id="d1", limits=FAST)
    assert report.degraded and report.missing_perspectives == ["black"]
    assert [(f.node, f.hat, f.error_type) for f in report.failures] == [
        ("black", "black", "RuntimeError")
    ]
    assert "black" in render_markdown(report) and "RuntimeError" in render_markdown(report)


async def test_failure_messages_never_contain_model_text():
    err = HttpError(500)
    err.args = ("secret prompt text sk-abcdefgh12345678",)
    model = make_hats_fake(_fail("white", err))
    report = await run_workflow(Q, lambda _n: model, run_id="d2", limits=FAST)
    dumped = report.model_dump_json()
    assert "secret prompt text" not in dumped and "sk-abcdefgh" not in dumped
    assert report.failures[0].message == "HTTP 500"


async def test_transient_error_is_retried_then_succeeds():
    seen = {"n": 0}

    def respond(kind, hat, messages):
        if hat == "red":
            seen["n"] += 1
            if seen["n"] == 1:
                return HttpError(503)
        return default_response(kind, hat, messages)

    model = make_hats_fake(respond)
    report = await run_workflow(Q, lambda _n: model, run_id="d3", limits=FAST)
    assert not report.degraded and seen["n"] == 2


async def test_non_transient_error_is_not_retried():
    seen = {"n": 0}

    def respond(kind, hat, messages):
        if hat == "red":
            seen["n"] += 1
            return HttpError(401)
        return default_response(kind, hat, messages)

    model = make_hats_fake(respond)
    report = await run_workflow(Q, lambda _n: model, run_id="d4", limits=FAST)
    assert seen["n"] == 1 and report.degraded


async def test_hung_hat_times_out_and_run_still_finishes():
    base = default_response

    class Slow(Exception): ...

    model = make_hats_fake(lambda k, h, m: base(k, h, m))
    original = model.with_structured_output

    def patched(schema, **kw):
        runnable = original(schema, **kw)
        if schema.__name__ != "HatOutput":
            return runnable

        async def answer(messages):
            if "GREEN HAT" in str(messages[0].content):
                await asyncio.sleep(5)
            return await runnable.ainvoke(messages)

        from langchain_core.runnables import RunnableLambda

        return RunnableLambda(lambda _m: None, afunc=answer)

    object.__setattr__(model, "with_structured_output", patched)
    limits = Limits(node_timeout_seconds=0.2, node_retries=0, retry_backoff_seconds=0)
    report = await run_workflow(Q, lambda _n: model, run_id="d5", limits=limits)
    assert report.missing_perspectives == ["green"]
    assert report.failures[0].error_type == "TimeoutError"


async def test_blue_close_failure_falls_back_to_a_code_built_report():
    model = make_hats_fake(_fail("BlueCloseOutput", RuntimeError("boom")))
    report = await run_workflow(Q, lambda _n: model, run_id="d6", limits=FAST)
    assert report.degraded and report.failures[-1].node == "blue_close"
    assert {s.hat for s in report.hat_summaries} == {"white", "red", "green", "yellow", "black"}
    assert "unavailable" in report.conclusions[0]


async def test_all_hats_failing_raises_all_hats_failed():
    model = make_hats_fake(_fail("HatOutput", RuntimeError("boom")))
    with pytest.raises(AllHatsFailedError):
        await run_workflow(Q, lambda _n: model, run_id="d7", limits=FAST)


async def test_config_error_is_never_degraded():
    model = make_hats_fake(_fail("HatOutput", ConfigError("bad key")))
    with pytest.raises(ConfigError):
        await run_workflow(Q, lambda _n: model, run_id="d8", limits=FAST)


async def test_sequential_step_failure_skips_the_step_and_continues():
    framing = default_framing().model_copy(
        update={"mode": "sequential", "sequence": ["white", "red", "green"]}
    )

    def respond(kind, hat, messages):
        if kind == "Framing":
            return framing
        if hat == "red":
            return RuntimeError("boom")
        return default_response(kind, hat, messages)

    model = make_hats_fake(respond)
    report = await run_workflow(Q, lambda _n: model, run_id="d9", limits=FAST)
    assert report.degraded and report.missing_perspectives == ["red"]
    green_user = next(c[2] for c in model.calls if c[1] == "green" and c[0] == "HatOutput")
    assert "white point 0" in green_user and "red point" not in green_user


def test_sequential_context_is_capped_oldest_first():
    from six_hats.hats.base import earlier_block
    from six_hats.schemas.hat_output import HatOutput

    steps = [
        (f"white#{i}", HatOutput(hat="white", key_points=[f"point {i} " + "x" * 400] * 3))
        for i in range(10)
    ]
    block = earlier_block(steps, max_chars=3000)
    assert "point 9" in block and "point 0 " not in block and "left out" in block


def test_is_transient():
    assert is_transient(TimeoutError()) and is_transient(HttpError(429))
    assert not is_transient(HttpError(401)) and not is_transient(ValueError())

    class APIConnectionError(Exception): ...

    assert is_transient(APIConnectionError())


async def test_run_guarded_returns_failure_record():
    async def boom():
        raise RuntimeError("x")

    result, failure = await run_guarded(boom, limits=FAST, node="n", run_id="r")
    assert result is None and failure is not None and failure.error_type == "RuntimeError"
