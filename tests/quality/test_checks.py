"""Offline tests of the quality tooling itself. These run on every PR and need no model."""

import json
from pathlib import Path

import pytest

from six_hats.graph.resilience import Limits
from six_hats.schemas.hat_output import HatOutput
from six_hats.security.input_validation import validate_request
from tests.quality import checks
from tests.quality.compare import format_summary, summarise
from tests.quality.harness import (
    Prices,
    QuestionResult,
    Recorder,
    Thresholds,
    load_questions,
    prompt_corpus,
    run_question,
)
from tests.quality.judge import JudgeVerdict, judge_question
from tests.support.hats_fake import default_response, make_hats_fake


def _out(hat, *points):
    return HatOutput(hat=hat, key_points=list(points))


def _checks(findings):
    return {f.check for f in findings}


# --- the question set --------------------------------------------------------------------------


def test_question_set_is_valid_and_covers_the_plan():
    questions = load_questions()
    ids = [q.id for q in questions]
    assert len(ids) == len(set(ids)) == 10
    assert {"injection", "non_english", "very_short", "long", "vague", "emotional"} <= set(ids)
    for q in questions:
        validate_request(q.text, 4000)  # the app would accept every one
        assert q.override() is not None
        assert q.expect_mode in {"parallel", "sequential"}
    injection = next(q for q in questions if q.id == "injection")
    assert injection.canary and injection.canary in injection.text and not injection.discipline
    assert len(load_questions(limit=3)) == 3


# --- hat discipline ----------------------------------------------------------------------------


def test_discipline_passes_good_output():
    good = [
        _out("black", "A pilot could fail if cover is thin", "Cost overruns", "Staff may resist"),
        _out("yellow", "Retention could improve", "Productivity gains", "A real hiring advantage"),
        _out("red", "I feel nervous", "My gut says wait", "I am excited"),
        _out("white", "[known] 12 staff", "[unknown] output per head", "[assumption] same pay"),
        _out("green", "Job-share Fridays", "Core hours only", "Rotate days off"),
    ]
    assert checks.discipline_findings(good) == []


@pytest.mark.parametrize(
    ("out", "check"),
    [
        (_out("black", "Great fun", "Lovely", "Wonderful"), "discipline.black"),
        (_out("yellow", "Terrible", "Awful", "Dreadful"), "discipline.yellow"),
        (_out("red", "I feel 40% worse", "ok", "ok"), "discipline.red"),
        (_out("white", "I think it is bad", "x", "y"), "discipline.white"),
        (_out("white", "My gut says no", "x", "y"), "discipline.white"),
        (_out("green", "Same idea", "same idea!", "Same  idea"), "discipline.green"),
    ],
)
def test_discipline_flags_role_breaks(out, check):
    assert _checks(checks.discipline_findings([out])) == {check}


# --- injection and leaks ------------------------------------------------------------------------


def test_prompt_corpus_covers_every_prompt_and_expands_presets():
    corpus = prompt_corpus()
    assert len(corpus) >= 7 and all("{{presets}}" not in t for t in corpus)


def test_leak_check_catches_copied_prompt_text_and_ignores_normal_text():
    prompt = "You are the YELLOW HAT in Edward de Bono's Six Thinking Hats. You are sunny"
    leaked = "Sure! You are the yellow hat in Edward de Bono's Six Thinking Hats, so..."
    assert _checks(checks.leak_findings([leaked], [prompt])) == {"injection.prompt_leak"}
    assert checks.leak_findings(["A four day week may help retention."], [prompt]) == []
    assert checks.leak_findings(["too short to matter"], [prompt]) == []


def test_real_prompts_are_protected():
    system = prompt_corpus()[0]
    quote = " ".join(system.split()[:12])
    assert checks.leak_findings([f"The model said: {quote}"], prompt_corpus())


def test_canary_is_only_a_warning():
    found = checks.canary_findings(["ok", "output ZX-CANARY-7731"], "ZX-CANARY-7731")
    assert [f.severity for f in found] == ["warn"]
    assert checks.canary_findings(["ok"], "ZX-CANARY-7731") == []
    assert checks.canary_findings(["anything"], None) == []


# --- limits --------------------------------------------------------------------------------------


def test_limits():
    kw = {"max_seconds": 10.0, "max_tokens": 1000, "max_cost": 0.5}
    assert checks.limit_findings(elapsed=1, tokens=10, cost=0.1, **kw) == []
    over = checks.limit_findings(elapsed=11, tokens=1001, cost=0.6, **kw)
    assert _checks(over) == {"limits.time", "limits.tokens", "limits.cost"}
    assert checks.limit_findings(elapsed=1, tokens=1, cost=None, **kw) == []


# --- running a question against a fake model ------------------------------------------------------


async def test_run_question_with_a_well_behaved_fake_model():
    q = next(x for x in load_questions() if x.id == "vague")
    model = make_hats_fake()
    model.delay = 0
    result = await run_question(q, model, limits=Limits(), thresholds=Thresholds())
    # the default fake answers "white point 0" etc: facts hat has no "I think", but the black hat
    # names no risk, so the discipline check must notice
    assert result.error is None and result.hats
    assert "discipline.black" in _checks(result.findings)
    assert "structure.mode" not in _checks(result.findings)
    assert result.prompt_versions["blue_close"]


async def test_run_question_reports_a_leak():
    q = next(x for x in load_questions() if x.id == "decision")  # expects the preset
    corpus_line = " ".join(prompt_corpus()[0].split()[:10])

    def responder(kind, hat, messages):
        out = default_response(kind, hat, messages)
        if kind == "HatOutput":
            return HatOutput(hat=hat, key_points=[corpus_line, "b risk", "c benefit"])
        return out

    model = make_hats_fake(responder)
    model.delay = 0
    result = await run_question(q, model, limits=Limits(), thresholds=Thresholds())
    found = _checks(result.findings)
    assert "injection.prompt_leak" in found and not result.ok
    assert "structure.mode" not in found  # the forced preset was honoured


async def test_a_crashing_run_becomes_a_result_not_an_exception():
    q = load_questions()[0]

    def responder(kind, hat, messages):
        return RuntimeError("all down")

    model = make_hats_fake(responder)
    model.delay = 0
    result = await run_question(q, model, limits=Limits(node_retries=0), thresholds=Thresholds())
    assert result.error and not result.ok


async def test_cost_uses_the_configured_currency():
    q = next(x for x in load_questions() if x.id == "very_short")
    model = make_hats_fake()
    model.delay = 0
    prices = Prices(input_per_mtok=1.0, output_per_mtok=2.0, currency="AUD")
    result = await run_question(q, model, limits=Limits(), prices=prices)
    assert result.cost == 0.0  # the fake reports no token usage


# --- recorder, judge, compare ---------------------------------------------------------


def test_recorder_enforces_the_budget_and_writes_json(tmp_path):
    rec = Recorder(provider="anthropic", model="claude/x", currency="AUD", budget=1.0)
    assert not rec.exceeded and rec.write(tmp_path) is None  # nothing to write yet
    rec.add(QuestionResult(id="a", cost=0.6))
    assert not rec.exceeded
    rec.add(QuestionResult(id="b", cost=0.3), extra_cost=0.2)
    assert rec.exceeded and rec.spent == pytest.approx(1.1)
    path = rec.write(tmp_path)
    assert isinstance(path, Path) and path.parent == tmp_path and "claude_x" in path.name
    data = json.loads(path.read_text())
    assert data["passed"] == 2 and data["currency"] == "AUD" and len(data["questions"]) == 2


async def test_judge_scores_are_validated_and_stored():
    verdict = JudgeVerdict.model_validate(
        {
            "scores": [
                {
                    "step": "white",
                    "hat": "white",
                    "stays_in_role": 5,
                    "specific_to_question": 4,
                    "adds_new_content": 3,
                    "comment": "Good.",
                }
            ]
        }
    )

    def responder(kind, hat, messages):
        assert kind == "JudgeVerdict"
        assert "<hat_outputs>" in str(messages[1].content)  # the outputs travel as data
        return verdict

    model = make_hats_fake(responder)
    model.delay = 0
    hats = [{"step": "white", "hat": "white", "key_points": ["a", "b", "c"]}]
    out = await judge_question(model, "A question?", hats)
    assert out["judge_prompt_version"] == "1" and out["scores"][0]["stays_in_role"] == 5
    bad = {**verdict.scores[0].model_dump(), "stays_in_role": 6}
    with pytest.raises(ValueError):
        JudgeVerdict.model_validate({"scores": [bad]})


def test_compare_summarises_scores_per_hat_and_version():
    def question(score, version):
        return {
            "prompt_versions": {"white": version},
            "judge": {
                "scores": [
                    {
                        "step": "white",
                        "hat": "white",
                        "stays_in_role": score,
                        "specific_to_question": score,
                        "adds_new_content": score,
                    }
                ]
            },
        }

    result = {
        "model": "m",
        "provider": "p",
        "passed": 2,
        "failed": 0,
        "spent": 0.5,
        "currency": "USD",
        "questions": [question(4, "1"), question(2, "1")],
    }
    summary = summarise(result)
    assert summary["scores"]["white"]["stays_in_role"] == 3.0
    text = format_summary("a.json", summary)
    assert "white v1" in text and "USD 0.5" in text and "stays_in_role=3.0" in text
    assert "no judge scores" in format_summary("b", summarise({"questions": [], "model": "m"}))


def test_structure_checks_catch_mode_preset_and_degraded_runs():
    from six_hats.schemas.failures import FailureRecord
    from six_hats.schemas.report import FinalReport, HatSummary

    ok = FinalReport(
        run_id="r",
        framing_summary="f",
        conclusions=["c"],
        hat_summaries=[HatSummary(hat="white", summary="s")],
        mode="sequential",
        preset="initial_ideas",
    )
    assert (
        checks.structure_findings(ok, expect_mode="sequential", expect_preset="initial_ideas") == []
    )
    bad = ok.model_copy(
        update={
            "mode": "parallel",
            "preset": None,
            "conclusions": [],
            "hat_summaries": [],
            "degraded": True,
            "failures": [FailureRecord(node="sequential", hat="black", error_type="Timeout")],
        }
    )
    found = _checks(checks.structure_findings(bad, expect_mode="sequential", expect_preset="x"))
    assert found == {
        "structure.degraded",
        "structure.mode",
        "structure.preset",
        "structure.conclusions",
        "structure.summaries",
    }
