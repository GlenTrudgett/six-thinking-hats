"""The web API: presets, streaming run, error mapping."""

import json

import pytest
from fastapi.testclient import TestClient

from six_hats.config.settings import Settings
from six_hats.interfaces import api, cli
from six_hats.llm.factory import ConfigError
from tests.support.hats_fake import make_hats_fake


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "create_model", lambda _cfg: make_hats_fake())
    return TestClient(api.create_app(Settings(_env_file=None)))


def _events(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_health_and_presets(client):
    assert client.get("/api/health").json()["status"] == "ok"
    body = client.get("/api/presets").json()
    assert body["hats"] == ["white", "red", "green", "yellow", "black"]
    assert {p["id"] for p in body["presets"]} >= {"quick_feedback", "initial_ideas"}


def test_run_streams_progress_then_report(client):
    r = client.post("/api/run", json={"question": "Should we do X?"})
    ev = _events(r.text)
    names = [e for e, _ in ev]
    assert names[0] == "start" and names[-1] == "report" and "progress" in names
    assert ev[-1][1]["conclusions"] and "token_usage" in ev[-1][1]


def test_run_with_preset_and_parallel(client):
    ev = _events(client.post("/api/run", json={"question": "q", "preset": "quick_feedback"}).text)
    assert ev[-1][1]["sequence"] == ["black", "green"]
    ev = _events(client.post("/api/run", json={"question": "q", "mode": "parallel"}).text)
    assert ev[-1][1]["mode"] == "parallel"


@pytest.mark.parametrize(
    "body",
    [
        {"question": "q", "preset": "nope"},
        {"question": "q", "preset": "quick_feedback", "mode": "parallel"},
        {"question": "q", "sequence": ["white"], "preset": "initial_ideas"},
    ],
)
def test_bad_choices_become_input_error_events(client, body):
    ev = _events(client.post("/api/run", json=body).text)
    assert ev[-1][0] == "error" and ev[-1][1]["kind"] == "input"


@pytest.mark.parametrize(
    "body", [{"question": ""}, {"question": "x" * 8001}, {"question": "q", "sequence": ["blue"]}]
)
def test_invalid_request_is_422(client, body):
    assert client.post("/api/run", json=body).status_code == 422


def test_config_error_does_not_leak_detail(monkeypatch):
    def boom(_cfg):
        raise ConfigError("key sk-ant-SECRET rejected")

    monkeypatch.setattr(api, "create_model", boom)
    c = TestClient(api.create_app(Settings(_env_file=None)))
    text = c.post("/api/run", json={"question": "q"}).text
    assert "SECRET" not in text and _events(text)[-1][1]["kind"] == "config"


def test_cors_only_for_local_frontend(client):
    ok = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_serve_command_exists():
    assert "serve" in [c.name or c.callback.__name__ for c in cli.app.registered_commands]
