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


from six_hats.config.settings import LLMSettings  # noqa: E402


def test_api_key_is_trimmed_and_blank_means_unset():
    assert (
        LLMSettings(anthropic_api_key="  sk-ant-abc123  \n").anthropic_api_key.get_secret_value()
        == "sk-ant-abc123"
    )  # type: ignore[union-attr]
    assert LLMSettings(anthropic_api_key="").anthropic_api_key is None
    assert LLMSettings(anthropic_api_key="   ").anthropic_api_key is None


def test_api_key_with_inner_whitespace_is_rejected_without_echoing_it():
    with pytest.raises(ValidationError) as exc:
        LLMSettings(anthropic_api_key="sk-ant-abc 123")
    assert "abc 123" not in str(exc.value)


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        ("anthropic", (2.0, 10.0, "USD")),
        ("local", (None, None, None)),
        ("demo", (None, None, None)),
    ],
)
def test_prices_only_for_anthropic(provider, expected):
    s = Settings(
        _env_file=None,
        llm={"provider": provider},
        run={"price_input_per_mtok": 2.0, "price_output_per_mtok": 10.0, "price_currency": "usd"},
    )
    assert s.prices() == expected
