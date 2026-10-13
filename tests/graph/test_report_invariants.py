"""Property-style checks: whatever the fake models do, the report obeys its rules."""

import asyncio
from collections import Counter

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from six_hats.graph.runner import run_workflow
from six_hats.schemas.hat_output import THINKING_HATS
from tests.support.hats_fake import default_framing, default_response, make_hats_fake

HAT = st.sampled_from(THINKING_HATS)
SETTINGS = settings(
    max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow], database=None
)


def _run(sequence, mode, kind, failing, fail_close=False, fail_open=False):
    framing = default_framing().model_copy(
        update={"sequence": sequence, "mode": mode, "thinking_type": kind}
    )

    def respond(schema, hat, messages):
        if schema == "Framing":
            return RuntimeError("down") if fail_open else framing
        if schema == "HatOutput" and hat in failing:
            return RuntimeError("down")
        if schema == "BlueCloseOutput" and fail_close:
            return RuntimeError("down")
        return default_response(schema, hat, messages)

    model = make_hats_fake(respond)
    model.delay = 0
    report = asyncio.run(run_workflow("A question?", lambda _n: model, run_id="prop"))
    return report, model


@SETTINGS
@given(
    sequence=st.lists(HAT, min_size=1, max_size=8),
    kind=st.sampled_from(["new_idea", "evaluation", "problem"]),
    failing=st.sets(HAT, max_size=5),
    fail_close=st.booleans(),
)
def test_sequential_report_invariants(sequence, kind, failing, fail_close):
    if set(sequence) <= failing:
        failing = set()  # every step failing is the "no output" error path, tested elsewhere
    report, model = _run(sequence, "sequential", kind, failing, fail_close)

    assert report.mode == "sequential" and len(report.sequence) <= 8
    assert "blue" not in report.sequence
    assert Counter(report.sequence) == Counter(sequence)  # rules may reorder, never add or drop
    calls = [c[1] for c in model.calls if c[0] == "HatOutput"]
    assert len(calls) == len(sequence)  # one call per step, repeats included
    summarised = [s.hat for s in report.hat_summaries]
    assert len(summarised) == len(set(summarised))  # one summary per hat
    produced = {h for h in set(sequence) if h not in failing}
    assert set(summarised) <= produced
    assert set(report.missing_perspectives) == set(sequence) & failing
    # degraded exactly when something failed
    assert report.degraded == bool(report.failures)
    assert len(report.failures) == sum(1 for h in sequence if h in failing) + int(fail_close)


@SETTINGS
@given(failing=st.sets(HAT, max_size=4), fail_close=st.booleans())
def test_parallel_report_invariants(failing, fail_close):
    report, model = _run(list(THINKING_HATS), "parallel", "evaluation", failing, fail_close)
    assert report.mode == "parallel" and report.sequence == [] and report.preset is None
    assert sorted(c[1] for c in model.calls if c[0] == "HatOutput") == sorted(THINKING_HATS)
    assert set(report.missing_perspectives) == failing
    assert report.degraded == bool(report.failures)
    assert {s.hat for s in report.hat_summaries} == set(THINKING_HATS) - failing


@SETTINGS
@given(sequence=st.lists(HAT, min_size=1, max_size=8), failing=st.sets(HAT, max_size=5))
def test_failed_hats_never_appear_as_covered(sequence, failing):
    if set(sequence) <= failing:
        failing = set()
    report, _ = _run(sequence, "sequential", "new_idea", failing)
    assert not ({s.hat for s in report.hat_summaries} & failing)


@SETTINGS
@given(kind=st.sampled_from(["new_idea", "evaluation", "problem"]))
def test_blue_open_failure_falls_back_to_all_five_hats(kind):
    report, model = _run(["white"], "sequential", kind, set(), fail_open=True)
    assert report.mode == "parallel" and report.degraded
    assert [f.node for f in report.failures] == ["blue_open"]
    assert len([c for c in model.calls if c[0] == "HatOutput"]) == 5
