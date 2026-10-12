from typer.testing import CliRunner

from six_hats.interfaces import cli
from six_hats.interfaces.diagnose import ping
from tests.support.hats_fake import make_hats_fake
from tests.support.json_fake import HttpError

runner = CliRunner()
KEY = "sk-ant-SECRETSECRET123456"


def test_diagnose_shows_facts_and_hides_the_key(monkeypatch):
    monkeypatch.setenv("SIXHATS_LLM__ANTHROPIC_API_KEY", KEY)
    result = runner.invoke(cli.app, ["diagnose"])
    assert result.exit_code == 0
    assert "anthropic api key" in result.output and "set" in result.output
    assert KEY not in result.output and KEY not in result.stderr
    assert "blue_close v2" in result.output and "langgraph" in result.output


def test_diagnose_without_key_exits_3(monkeypatch):
    monkeypatch.delenv("SIXHATS_LLM__ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir("/")  # no .env to pick up
    result = runner.invoke(cli.app, ["diagnose"])
    assert result.exit_code == 3 and "NOT SET" in result.output
    assert "PROBLEM" in result.stderr


def test_diagnose_invalid_setting_exits_3_without_echoing_value(monkeypatch):
    monkeypatch.setenv("SIXHATS_LLM__TEMPERATURE", "banana-" + KEY)
    result = runner.invoke(cli.app, ["diagnose"])
    assert result.exit_code == 3 and KEY not in result.stderr + result.output


def test_diagnose_local_provider(monkeypatch):
    monkeypatch.setenv("SIXHATS_LLM__PROVIDER", "local")
    result = runner.invoke(cli.app, ["diagnose"])
    assert result.exit_code == 0 and "127.0.0.1" in result.output


def test_ping_success_and_failure_exit_codes(monkeypatch):
    monkeypatch.setenv("SIXHATS_LLM__PROVIDER", "local")

    class Good:
        async def ainvoke(self, _p):
            return "ok"

    class Bad:
        async def ainvoke(self, _p):
            raise HttpError(401)

    monkeypatch.setattr(cli, "create_model", lambda _cfg: Good())
    assert runner.invoke(cli.app, ["diagnose", "--ping"]).exit_code == 0
    monkeypatch.setattr(cli, "create_model", lambda _cfg: Bad())
    bad = runner.invoke(cli.app, ["diagnose", "--ping"])
    assert bad.exit_code == 5 and "HttpError HTTP 401" in bad.output


async def test_ping_shows_underlying_error_types_not_messages():
    class Inner(OSError): ...

    class Outer(Exception): ...

    class Broken:
        async def ainvoke(self, _p):
            try:
                raise Inner("secret host sk-abcdefgh12345678")
            except Inner as inner:
                raise Outer("wrapped") from inner

    ok, detail = await ping(Broken())  # type: ignore[arg-type]
    assert not ok and detail == "Outer <- Inner"
    assert "secret" not in detail


async def test_ping_reports_timeout():
    import asyncio

    class Slow:
        async def ainvoke(self, _p):
            await asyncio.sleep(5)

    ok, detail = await ping(Slow(), timeout=0.05)  # type: ignore[arg-type]
    assert not ok and "TimeoutError" in detail
    assert make_hats_fake() is not None
