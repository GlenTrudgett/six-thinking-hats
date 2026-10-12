"""Phase 3: sequential mode runs hats one at a time, each seeing what came before."""

import pytest

from six_hats.graph.runner import run_workflow
from six_hats.graph.sequence import apply_sequence_rules, step_key
from six_hats.schemas.framing import Framing
from tests.support.hats_fake import default_framing, default_response, make_hats_fake

Q = "Should we adopt a four-day work week?"


def _framing(sequence, thinking_type="new_idea", mode="sequential") -> Framing:
    return default_framing().model_copy(
        update={"sequence": sequence, "thinking_type": thinking_type, "mode": mode}
    )


def _responder(framing):
    def respond(kind, hat, messages):
        return framing if kind == "Framing" else default_response(kind, hat, messages)

    return respond


async def test_hats_run_in_sequence_and_see_earlier_output():
    model = make_hats_fake(_responder(_framing(["white", "green", "red"])))
    report = await run_workflow(Q, lambda _n: model, run_id="s1")

    hats = [(c[1], c[2]) for c in model.calls if c[0] == "HatOutput"]
    assert [h for h, _ in hats] == ["white", "green", "red"]  # exactly the sequence, in order
    assert "<earlier_hats>" not in hats[0][1]  # the first hat sees nothing
    assert "white point 0" in hats[1][1] and "green point" not in hats[1][1]
    assert "white point 0" in hats[2][1] and "green point 0" in hats[2][1]
    assert report.mode == "sequential" and report.sequence == ["white", "green", "red"]


async def test_skipped_hats_are_not_reported_missing():
    model = make_hats_fake(_responder(_framing(["white", "green"])))
    report = await run_workflow(Q, lambda _n: model, run_id="s2")
    assert report.missing_perspectives == [] and not report.degraded


async def test_a_hat_can_repeat_and_each_step_is_kept():
    model = make_hats_fake(_responder(_framing(["white", "green", "white"])))
    await run_workflow(Q, lambda _n: model, run_id="s3")
    close_user = next(c[2] for c in model.calls if c[0] == "BlueCloseOutput")
    assert '"white"' in close_user and '"white#2"' in close_user
    assert [c[1] for c in model.calls if c[0] == "HatOutput"] == ["white", "green", "white"]


async def test_untrusted_hat_output_stays_inside_the_data_block():
    model = make_hats_fake(_responder(_framing(["white", "red"])))
    await run_workflow(Q, lambda _n: model, run_id="s4")
    red_user = next(c[2] for c in model.calls if c[1] == "red" and c[0] == "HatOutput")
    assert "<earlier_hats>" in red_user and red_user.rstrip().endswith("</earlier_hats>")


def test_yellow_goes_before_black_in_an_evaluation():
    fixed, changed = apply_sequence_rules(_framing(["white", "black", "yellow"], "evaluation"))
    assert changed and fixed.sequence == ["white", "yellow", "black"]


@pytest.mark.parametrize(
    ("seq", "kind"),
    [(["black", "yellow"], "new_idea"), (["white", "yellow", "black"], "evaluation")],
)
def test_other_sequences_are_left_alone(seq, kind):
    fixed, changed = apply_sequence_rules(_framing(seq, kind))
    assert not changed and fixed.sequence == seq


async def test_blue_open_corrects_black_before_yellow():
    model = make_hats_fake(_responder(_framing(["black", "yellow"], "evaluation")))
    await run_workflow(Q, lambda _n: model, run_id="s5")
    assert [c[1] for c in model.calls if c[0] == "HatOutput"] == ["yellow", "black"]


def test_step_keys():
    assert step_key("white", []) == "white"
    assert step_key("white", ["white"]) == "white#2"
    assert step_key("white", ["white", "red", "white"]) == "white#3"


def test_sequence_length_is_capped():
    with pytest.raises(ValueError):
        Framing(focus="f", objective="o", thinking_type="new_idea", sequence=["white"] * 9)


async def test_report_markdown_shows_the_sequence():
    from six_hats.reporting.render import render_markdown

    model = make_hats_fake(_responder(_framing(["white", "red"])))
    report = await run_workflow(Q, lambda _n: model, run_id="s6")
    assert "Sequence: Blue → White → Red → Blue" in render_markdown(report)
