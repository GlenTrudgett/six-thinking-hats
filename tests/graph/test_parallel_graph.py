"""Phase 2 exit criteria: fan-in works and blue_close runs exactly once, after all hats."""

import pytest

from six_hats.graph.builder import build_graph
from six_hats.graph.runner import run_workflow
from six_hats.schemas.hat_output import THINKING_HATS
from six_hats.security.input_validation import InputError
from tests.support.hats_fake import default_framing, default_response, make_hats_fake

Q = "Should we adopt a four-day work week?"


def _kinds(model):
    return [c[0] for c in model.calls]


async def test_fan_in_and_single_blue_close():
    model = make_hats_fake()
    report = await run_workflow(Q, lambda _n: model, run_id="r1")

    assert _kinds(model).count("BlueCloseOutput") == 1
    assert _kinds(model).count("Framing") == 1
    hats_called = sorted(c[1] for c in model.calls if c[0] == "HatOutput")
    assert hats_called == sorted(THINKING_HATS)  # each hat exactly once

    kinds = _kinds(model)
    close_at = kinds.index("BlueCloseOutput")
    assert close_at == len(kinds) - 1  # last call
    assert kinds.index("Framing") == 0  # first call
    assert all(k == "HatOutput" for k in kinds[1:close_at])  # only hats in between
    assert not report.degraded and report.run_id == "r1"


async def test_blue_close_sees_all_five_outputs():
    model = make_hats_fake()
    await run_workflow(Q, lambda _n: model, run_id="r2")
    close_user = next(c[2] for c in model.calls if c[0] == "BlueCloseOutput")
    for hat in THINKING_HATS:
        assert f'"{hat}"' in close_user
    assert "<missing_hats>\nnone\n</missing_hats>" in close_user


async def test_parallel_hats_do_not_see_each_other():
    model = make_hats_fake()
    await run_workflow(Q, lambda _n: model, run_id="r3")
    for kind, hat, user in model.calls:
        if kind != "HatOutput":
            continue
        for other in THINKING_HATS:
            assert f"{other} point" not in user, f"{hat} saw output of {other}"


async def test_hats_run_concurrently():
    """With a 50 ms delay each, five serial hats would take >= 250 ms."""
    import time

    model = make_hats_fake()
    model.delay = 0.05
    start = time.perf_counter()
    await run_workflow(Q, lambda _n: model, run_id="r4")
    hats_elapsed = time.perf_counter() - start - 0.1  # minus blue_open and blue_close
    assert hats_elapsed < 0.2


async def test_report_metadata_comes_from_code():
    def responder(kind, hat, messages):
        out = default_response(kind, hat, messages)
        if kind == "BlueCloseOutput":
            # model tries to invent a hat summary for a hat and to look "not degraded"
            out.hat_summaries = out.hat_summaries + out.hat_summaries[:1]
        return out

    model = make_hats_fake(responder)
    report = await run_workflow(Q, lambda _n: model, run_id="r5")
    assert [s.hat for s in report.hat_summaries].count("white") == 1  # de-duplicated
    assert report.prompt_versions["blue_close"] == "3" and report.prompt_versions["black"] == "1"
    assert report.missing_perspectives == []


async def test_missing_hat_output_is_reported_as_degraded():
    from six_hats.graph.nodes import _assemble_report
    from six_hats.schemas.hat_output import HatOutput
    from six_hats.schemas.report import BlueCloseOutput

    closing = default_response("BlueCloseOutput", "x", [])
    assert isinstance(closing, BlueCloseOutput)
    state = {"outputs": {"white": HatOutput(hat="white", key_points=["a", "b", "c"])}}
    report = _assemble_report("r6", closing, ["red", "green", "yellow", "black"], state)
    assert report.degraded and report.missing_perspectives == ["red", "green", "yellow", "black"]
    assert [s.hat for s in report.hat_summaries] == ["white"]  # summaries of absent hats dropped


async def test_intake_rejects_bad_input_before_any_model_call():
    model = make_hats_fake()
    with pytest.raises(InputError):
        await run_workflow("   ", lambda _n: model, run_id="r7")
    with pytest.raises(InputError):
        await run_workflow("x" * 50, lambda _n: model, run_id="r8", max_question_chars=10)
    assert model.calls == []


async def test_blue_open_failure_falls_back_to_default_framing():
    def responder(kind, hat, messages):
        if kind == "Framing":
            return {"focus": "f", "objective": "o", "thinking_type": "x", "sequence": ["purple"]}
        return default_response(kind, hat, messages)

    model = make_hats_fake(responder)
    report = await run_workflow(Q, lambda _n: model, run_id="r9")
    assert report.degraded and report.mode == "parallel"
    assert [f.node for f in report.failures] == ["blue_open"]
    assert sorted(c[1] for c in model.calls if c[0] == "HatOutput") == sorted(THINKING_HATS)


def test_no_checkpointer_attached_by_default():
    graph = build_graph(lambda _n: make_hats_fake())
    assert graph.checkpointer is None


def test_graph_topology():
    g = build_graph(lambda _n: make_hats_fake()).get_graph()
    nodes = set(g.nodes)
    assert {"intake", "blue_open", "blue_close", *THINKING_HATS} <= nodes
    into_close = {e.source for e in g.edges if e.target == "blue_close"}
    assert into_close == {*THINKING_HATS, "sequential"}


async def test_streaming_updates_expose_no_private_channels(capsys):
    """Runner streams updates only, so logs carry node names and key names, never content."""
    from six_hats.observability.logging import configure_logging

    configure_logging("DEBUG", json=True)
    model = make_hats_fake()
    await run_workflow("secret-question-text", lambda _n: model, run_id="r10")
    err = capsys.readouterr().err
    assert "secret-question-text" not in err and "white point" not in err
    assert "run.started" in err and "run.completed" in err


async def test_framing_default_is_valid():
    assert default_framing().sequence == list(THINKING_HATS)
