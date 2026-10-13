"""The offline demo provider runs the whole workflow with no key and no network."""

from typer.testing import CliRunner

from six_hats.config.settings import LLMSettings
from six_hats.graph.runner import run_workflow
from six_hats.interfaces import cli
from six_hats.llm.demo import DemoChatModel
from six_hats.llm.factory import create_model
from six_hats.schemas.presets import SequenceOverride


def _model() -> DemoChatModel:
    m = create_model(LLMSettings(provider="demo"))
    assert isinstance(m, DemoChatModel)
    m.delay = 0
    return m


async def test_demo_runs_parallel_and_reports_usage():
    m = _model()
    report = await run_workflow("Is this a good idea?", lambda _n: m, run_id="d1")
    assert report.models_used == ["demo"] and not report.degraded
    assert report.token_usage["input_tokens"] > 0
    assert all("demo" in s.summary for s in report.hat_summaries)


async def test_demo_runs_a_preset_sequence():
    m = _model()
    report = await run_workflow(
        "q", lambda _n: m, run_id="d2", override=SequenceOverride(preset="quick_feedback")
    )
    assert report.sequence == ["black", "green"] and not report.degraded


def test_demo_via_cli_and_diagnose(monkeypatch):
    monkeypatch.setenv("SIXHATS_LLM__PROVIDER", "demo")
    r = CliRunner().invoke(cli.app, ["run", "q", "-q"])
    assert r.exit_code == 0 and "demo" in r.output
    d = CliRunner().invoke(cli.app, ["diagnose"])
    assert d.exit_code == 0 and "offline" in d.output
