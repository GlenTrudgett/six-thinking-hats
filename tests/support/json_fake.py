"""Chat models for exercising the structured-output fallback."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage


class HttpError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


class NoStructuredModel(GenericFakeChatModel):
    """with_structured_output fails like a server without tool or schema support."""

    error: Exception = NotImplementedError()

    def with_structured_output(self, schema: Any, **_: Any) -> Any:
        raise self.error


def replies(*texts: str) -> Iterator[AIMessage]:
    return iter([AIMessage(content=t) for t in texts])


def no_structured(*texts: str, error: Exception | None = None) -> NoStructuredModel:
    return NoStructuredModel(
        messages=replies(*texts), error=error if error is not None else NotImplementedError()
    )
