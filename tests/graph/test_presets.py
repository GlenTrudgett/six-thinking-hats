"""Presets: code-owned orders, caller overrides, and the CLI."""

import pytest
from typer.testing import CliRunner

from six_hats.graph.runner import run_workflow
from six_hats.graph.sequence import resolve_order
from six_hats.interfaces import cli
from six_hats.schemas.presets import MAX_SEQUENCE_STEPS, PRESETS, PresetId, SequenceOverride
from tests.support.hats_fake import default_framing, default_response, make_hats_fake

Q = "Should we adopt a four-day work week?"
HATS = {"white", "red", "green", "yellow", "black"}


def test_preset_ids_match_literal():
    assert set(PresetId.__args__) == set(PRESETS)  # type: ignore[attr-defined]


@pytest.mark.parametrize("p", PRESETS.values(), ids=lambda p: p.id)
def test_every_preset_is_valid(p):
    assert 1 <= len(p.sequence) <= MAX_SEQUENCE_STEPS
    assert set(p.sequence) <= HATS and p.source == "unverified"


def test_override_needs_exactly_one():
    with pytest.raises(ValueError):
        SequenceOverride()
    with pytest.raises(ValueError):
        SequenceOverride(preset="quick_feedback", sequence=["white"])


def _responder(framing):
    def respond(kind, hat, messages):
        return framing if kind == "Framing" else default_response(kind, hat, messages)

    return respond


def test_model_chosen_preset_gets_code_order():
    f = default_framing().model_copy(
        update={"preset": "quick_feedback", "sequence": ["red", "white"], "mode": "parallel"}
    )
    fixed, how = resolve_order(f, None)
    assert how == "preset" and fixed.sequence == ["black", "green"] and fixed.mode == "sequential"


def test_override_beats_blue_open():
    f = default_framing().model_copy(update={"preset": "quick_feedback"})
    fixed, how = resolve_order(f, SequenceOverride(sequence=["red", "red"]))
    assert how == "override" and fixed.sequence == ["red", "red"] and fixed.preset == "custom"


async def test_report_carries_preset_and_renders():
    model = make_hats_fake()
    ov = SequenceOverride(preset="initial_ideas")
    report = await run_workflow(Q, lambda _n: model, run_id="p1", override=ov)
    assert report.preset == "initial_ideas" and report.preset_source == "unverified"
    assert report.sequence == ["white", "green"]
    assert [c[1] for c in model.calls if c[0] == "HatOutput"] == ["white", "green"]
    from six_hats.reporting.render import render_markdown

    assert "Preset:" in render_markdown(report)


async def test_prompt_lists_all_presets():
    seen: list[str] = []

    def respond(kind, hat, messages):
        if kind == "Framing":
            seen.append(str(messages[0].content))
        return default_response(kind, hat, messages)

    model = make_hats_fake(respond)
    await run_workflow(Q, lambda _n: model, run_id="p2")
    assert "{{presets}}" not in seen[0]
    assert all(pid in seen[0] for pid in PRESETS)


runner = CliRunner()


def _use(monkeypatch):
    monkeypatch.setattr(cli, "create_model", lambda _cfg: make_hats_fake())
    monkeypatch.setenv("SIXHATS_LLM__API_KEY", "sk-ant-test")


def test_presets_command_lists_all():
    out = runner.invoke(cli.app, ["presets"]).output
    assert all(pid in out for pid in PRESETS) and "unverified" in out


def test_cli_preset_and_sequence(monkeypatch):
    _use(monkeypatch)
    r = runner.invoke(cli.app, ["run", "q", "--preset", "quick_feedback", "--format", "json"])
    assert r.exit_code == 0 and '"black"' in r.output
    r = runner.invoke(cli.app, ["run", "q", "--sequence", "white, green"])
    assert (r.exit_code == 0 and "White → Green" in r.output) or "white" in r.output.lower()


@pytest.mark.parametrize(
    "args",
    [
        ["--preset", "nope"],
        ["--sequence", "white,blue"],
        ["--sequence", "white," * 9 + "red"],
        ["--preset", "quick_feedback", "--sequence", "white"],
    ],
)
def test_cli_bad_options_exit_2(monkeypatch, args):
    _use(monkeypatch)
    assert runner.invoke(cli.app, ["run", "q", *args]).exit_code == 2


async def test_parallel_override_beats_a_preset_chosen_by_blue():
    f = default_framing().model_copy(update={"preset": "quick_feedback", "mode": "sequential"})
    model = make_hats_fake(_responder(f))
    report = await run_workflow(
        Q, lambda _n: model, run_id="par1", override=SequenceOverride(parallel=True)
    )
    assert report.mode == "parallel" and report.preset is None
    assert {c[1] for c in model.calls if c[0] == "HatOutput"} == HATS


def test_override_parallel_conflicts():
    with pytest.raises(ValueError):
        SequenceOverride(parallel=True, preset="quick_feedback")
    with pytest.raises(ValueError):
        SequenceOverride(parallel=True, sequence=["white"])


def test_cli_mode_parallel(monkeypatch):
    _use(monkeypatch)
    r = runner.invoke(cli.app, ["run", "q", "--mode", "parallel", "--format", "json"])
    assert r.exit_code == 0 and '"mode": "parallel"' in r.output.replace('":"', '": "')
    assert (
        runner.invoke(
            cli.app, ["run", "q", "--mode", "parallel", "--preset", "initial_ideas"]
        ).exit_code
        == 2
    )
    assert runner.invoke(cli.app, ["run", "q", "--mode", "nope"]).exit_code == 2
