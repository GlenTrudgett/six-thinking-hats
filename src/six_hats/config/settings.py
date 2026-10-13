"""Typed configuration. Secrets are SecretStr and never logged."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_loopback(host: str | None) -> bool:
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


class LocalServerSettings(BaseModel):
    base_url: str = "http://127.0.0.1:11434/v1"
    api_key: SecretStr = SecretStr("not-needed")
    allow_non_loopback: bool = False

    @model_validator(mode="after")
    def _check_loopback(self) -> LocalServerSettings:
        host = urlparse(self.base_url).hostname
        if not self.allow_non_loopback and not _is_loopback(host):
            raise ValueError(
                "local server base_url must be loopback unless allow_non_loopback is true"
            )
        return self


class LLMSettings(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)  # an error must never echo a key

    provider: Literal["anthropic", "local"] = "anthropic"
    model: str = "claude-sonnet-5-5"
    anthropic_api_key: SecretStr | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    @field_validator("anthropic_api_key", mode="before")
    @classmethod
    def _clean_key(cls, value: object) -> object:
        """Trim stray whitespace (a trailing space breaks the HTTP header); blank means not set."""
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if not isinstance(raw, str):
            return value
        key = raw.strip()
        if not key:
            return None
        if any(ch.isspace() for ch in key):
            raise ValueError("the API key contains whitespace; check for a line break or space")
        return key

    max_retries: int = Field(default=2, ge=0, le=5)
    timeout_seconds: float = Field(default=60.0, gt=0)
    local: LocalServerSettings = LocalServerSettings()


class RunSettings(BaseModel):
    max_input_chars: int = Field(default=8000, gt=0)
    mode: Literal["parallel", "sequential"] = "parallel"
    node_timeout_seconds: float = Field(default=120.0, gt=0)
    node_retries: int = Field(default=1, ge=0, le=5)
    retry_backoff_seconds: float = Field(default=1.0, ge=0)
    max_context_chars: int = Field(default=24_000, ge=1000)
    # Optional prices per million tokens. Unset: show tokens only (prices change; none built in).
    price_input_per_mtok: float | None = Field(default=None, ge=0)
    price_output_per_mtok: float | None = Field(default=None, ge=0)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SIXHATS_", env_nested_delimiter="__", env_file=".env", extra="ignore"
    )

    llm: LLMSettings = LLMSettings()
    run: RunSettings = RunSettings()
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = False


def load_settings() -> Settings:
    return Settings()
