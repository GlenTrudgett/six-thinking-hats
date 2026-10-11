"""ModelFactory: the single place a provider is chosen."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from six_hats.config.settings import LLMSettings


class ConfigError(RuntimeError):
    """Raised for missing or invalid model configuration (CLI exit code 3)."""


def create_model(cfg: LLMSettings) -> BaseChatModel:
    if cfg.provider == "anthropic":
        if cfg.anthropic_api_key is None:
            raise ConfigError("SIXHATS_LLM__ANTHROPIC_API_KEY is not set")
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=cfg.model,
            api_key=cfg.anthropic_api_key,
            temperature=cfg.temperature,
            max_retries=cfg.max_retries,
            timeout=cfg.timeout_seconds,
        )
    if cfg.provider == "local":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=cfg.model,
            base_url=cfg.local.base_url,
            api_key=cfg.local.api_key,
            temperature=cfg.temperature,
            max_retries=cfg.max_retries,
            timeout=cfg.timeout_seconds,
        )
    raise ConfigError(f"unknown provider: {cfg.provider}")
