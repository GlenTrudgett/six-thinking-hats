import pytest
from pydantic import ValidationError

from six_hats.config.settings import LocalServerSettings, Settings


def test_defaults():
    s = Settings(_env_file=None)
    assert s.llm.provider == "anthropic"
    assert s.llm.max_retries == 2


def test_secret_not_in_repr(monkeypatch):
    monkeypatch.setenv("SIXHATS_LLM__ANTHROPIC_API_KEY", "sk-supersecretvalue123")
    s = Settings(_env_file=None)
    assert "supersecret" not in repr(s)
    assert "supersecret" not in s.model_dump_json()


def test_local_url_must_be_loopback():
    with pytest.raises(ValidationError):
        LocalServerSettings(base_url="http://10.0.0.5:8000/v1")


def test_local_url_loopback_ok_and_override():
    LocalServerSettings(base_url="http://localhost:8000/v1")
    LocalServerSettings(base_url="http://10.0.0.5:8000/v1", allow_non_loopback=True)


def test_env_nested(monkeypatch):
    monkeypatch.setenv("SIXHATS_LLM__PROVIDER", "local")
    assert Settings(_env_file=None).llm.provider == "local"
