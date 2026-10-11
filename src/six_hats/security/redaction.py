"""Redact secrets from log events and strings."""

from __future__ import annotations

import re
from collections.abc import MutableMapping
from typing import Any

_KEY_HINTS = ("key", "token", "secret", "password", "authorization")
_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}"),
]
REDACTED = "***REDACTED***"


def redact_text(text: str) -> str:
    for pattern in _PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text


def redact_value(value: Any, key: str = "") -> Any:
    if any(hint in key.lower() for hint in _KEY_HINTS):
        return REDACTED
    if isinstance(value, dict):
        return {k: redact_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact_value(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    if type(value).__name__ == "SecretStr":
        return REDACTED
    return value


def redact_processor(
    _logger: Any, _name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    return {k: redact_value(v, k) for k, v in event_dict.items()}
