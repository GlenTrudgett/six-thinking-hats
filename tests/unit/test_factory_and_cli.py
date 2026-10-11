import pytest
from typer.testing import CliRunner

from six_hats.config.settings import LLMSettings
from six_hats.interfaces.cli import app
from six_hats.llm.factory import ConfigError, create_model

runner = CliRunner()


def test_anthropic_requires_key():
    with pytest.raises(ConfigError):
        create_model(LLMSettings(provider="anthropic"))


def test_builds_anthropic_and_local():
    assert create_model(LLMSettings(anthropic_api_key="k")).__class__.__name__ == "ChatAnthropic"
    assert create_model(LLMSettings(provider="local", model="m")).__class__.__name__ == "ChatOpenAI"


def test_cli_version_and_hats():
    assert "0.1.0" in runner.invoke(app, ["version"]).output
    out = runner.invoke(app, ["hats"]).output
    assert "white" in out and "[ready]" in out


def test_cli_exit_codes(monkeypatch):
    monkeypatch.delenv("SIXHATS_LLM__ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir("/")  # avoid picking up a repo .env
    assert runner.invoke(app, ["run", "   "]).exit_code == 2
    assert runner.invoke(app, ["run", "idea", "--hat", "red"]).exit_code == 2
    assert runner.invoke(app, ["run", "idea"]).exit_code == 3
