import pytest

from six_hats.config.settings import LLMSettings
from six_hats.llm.factory import ConfigError, create_model


def test_anthropic_requires_key():
    with pytest.raises(ConfigError):
        create_model(LLMSettings(provider="anthropic"))


def test_builds_anthropic_and_local():
    assert create_model(LLMSettings(anthropic_api_key="k")).__class__.__name__ == "ChatAnthropic"
    assert create_model(LLMSettings(provider="local", model="m")).__class__.__name__ == "ChatOpenAI"
