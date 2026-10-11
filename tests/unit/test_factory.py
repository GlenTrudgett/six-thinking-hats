import pytest

from six_hats.config.settings import LLMSettings
from six_hats.llm.factory import ConfigError, create_model


def test_anthropic_requires_key():
    with pytest.raises(ConfigError):
        create_model(LLMSettings(provider="anthropic"))


def test_builds_anthropic_and_local():
    assert create_model(LLMSettings(anthropic_api_key="k")).__class__.__name__ == "ChatAnthropic"
    assert create_model(LLMSettings(provider="local", model="m")).__class__.__name__ == "ChatOpenAI"


@pytest.mark.parametrize("model", ["claude-sonnet-5-5", "claude-fable-5-1"])
def test_fixed_sampling_models_get_no_temperature(model):
    chat = create_model(LLMSettings(anthropic_api_key="k", model=model, temperature=0.2))
    assert chat.temperature is None


def test_other_models_keep_configured_temperature():
    chat = create_model(
        LLMSettings(anthropic_api_key="k", model="claude-haiku-4-5", temperature=0.2)
    )
    assert chat.temperature == 0.2
