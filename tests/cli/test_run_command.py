import json

import pytest
from typer.testing import CliRunner

from six_hats.interfaces import cli
from six_hats.llm.factory import ConfigError
from tests.support.hats_fake import default_response, make_hats_fake

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    monkeypatch.chdir("/")  # avoid picking up a repo .env
    monkeypatch.delenv("SIXHATS_LLM__ANTHROPIC_API_KEY", raising=False)


def _use(monkeypatch, model):
    monkeypatch.setattr(cli, "create_model", lambda _cfg: model)


def test_version_and_hats():
    assert "0.2.0" in runner.invoke(cli.app, ["version"]).output
    out = runner.invoke(cli.app, ["hats"]).output
    for hat in ("white", "red", "green", "yellow", "black", "blue"):
        assert hat in out
    assert "blue_open v2" in out and "blue_close v2" in out


def test_run_markdown_text_argument(monkeypatch):
    _use(monkeypatch, make_hats_fake())
    result = runner.invoke(cli.app, ["run", "Should we do X?"])
    assert result.exit_code == 0, result.output
    assert "# Six Thinking Hats report" in result.stdout
    assert "run: " in result.stderr  # run id shown


def test_run_json_format(monkeypatch):
    _use(monkeypatch, make_hats_fake())
    result = runner.invoke(cli.app, ["run", "q", "--format", "json"])
    data = json.loads(result.stdout)
    assert result.exit_code == 0 and len(data["run_id"]) == 12 and data["degraded"] is False


def test_run_reads_stdin(monkeypatch):
    model = make_hats_fake()
    _use(monkeypatch, model)
    result = runner.invoke(cli.app, ["run", "-"], input="a question via stdin\n")
    assert result.exit_code == 0
    assert any("a question via stdin" in c[2] for c in model.calls)


def test_run_reads_file(monkeypatch, tmp_path):
    f = tmp_path / "q.txt"
    f.write_text("question from file", encoding="utf-8")
    model = make_hats_fake()
    _use(monkeypatch, model)
    assert runner.invoke(cli.app, ["run", "--file", str(f)]).exit_code == 0
    assert any("question from file" in c[2] for c in model.calls)


def test_output_file_and_overwrite_guard(monkeypatch, tmp_path):
    _use(monkeypatch, make_hats_fake())
    out = tmp_path / "report.md"
    assert runner.invoke(cli.app, ["run", "q", "-o", str(out)]).exit_code == 0
    assert "Six Thinking Hats report" in out.read_text(encoding="utf-8")
    again = runner.invoke(cli.app, ["run", "q", "-o", str(out)])
    assert again.exit_code == 2 and "--force" in again.stderr
    assert runner.invoke(cli.app, ["run", "q", "-o", str(out), "--force"]).exit_code == 0


@pytest.mark.parametrize(
    "args,stdin",
    [
        (["run"], None),
        (["run", "   "], None),
        (["run", "-"], "\n"),
        (["run", "q", "--file", "/nonexistent"], None),
    ],
)
def test_input_errors_exit_2(monkeypatch, args, stdin):
    _use(monkeypatch, make_hats_fake())
    assert runner.invoke(cli.app, args, input=stdin).exit_code == 2


def test_oversized_question_exit_2(monkeypatch):
    _use(monkeypatch, make_hats_fake())
    assert runner.invoke(cli.app, ["run", "x" * 9000]).exit_code == 2


def test_missing_api_key_exit_3():
    result = runner.invoke(cli.app, ["run", "q"])
    assert result.exit_code == 3 and "config error" in result.stderr


def test_config_error_message_has_no_secret(monkeypatch):
    def boom(_cfg):
        raise ConfigError("SIXHATS_LLM__ANTHROPIC_API_KEY is not set")

    monkeypatch.setattr(cli, "create_model", boom)
    assert runner.invoke(cli.app, ["run", "q"]).exit_code == 3


def test_invalid_model_output_exit_1_with_run_id(monkeypatch):
    def responder(kind, hat, messages):
        if kind == "HatOutput":
            return {"hat": hat, "key_points": []}
        return default_response(kind, hat, messages)

    _use(monkeypatch, make_hats_fake(responder))
    result = runner.invoke(cli.app, ["run", "q"])
    assert result.exit_code == 1 and "run " in result.stderr
