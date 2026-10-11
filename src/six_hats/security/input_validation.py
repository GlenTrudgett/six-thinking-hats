"""Validate user-supplied request text before it reaches any model."""

from __future__ import annotations

import unicodedata


class InputError(ValueError):
    """Raised for invalid user input (CLI exit code 2)."""


def validate_request(text: str, max_chars: int) -> str:
    cleaned = "".join(
        ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C"
    ).strip()
    if not cleaned:
        raise InputError("request is empty")
    if len(cleaned) > max_chars:
        raise InputError(f"request exceeds {max_chars} characters")
    return cleaned
