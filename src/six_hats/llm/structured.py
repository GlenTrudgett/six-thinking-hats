"""Get schema-valid output from any chat model.

Methods are tried in order. A method the provider or server does not support
(NotImplementedError, or HTTP 400/404/422) moves on to the next one.
Invalid output gets one bounded repair retry in total.
Anything else, such as an authentication or connection error, is raised unchanged.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ValidationError

Method = Literal["native", "function_calling", "json_mode"]
DEFAULT_METHODS: tuple[Method, ...] = ("native", "json_mode")
MAX_VALIDATION_ATTEMPTS = 2
_CAPABILITY_STATUS = {400, 404, 422}
_FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


class StructuredOutputError(RuntimeError):
    pass


def _is_capability_error(exc: Exception) -> bool:
    return isinstance(exc, NotImplementedError) or getattr(exc, "status_code", None) in (
        _CAPABILITY_STATUS
    )


def extract_json(text: str) -> str:
    """Pull the JSON object out of a reply that may include code fences or prose."""
    cleaned = _FENCE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("reply contains no JSON object")
    return cleaned[start : end + 1]


def _reply_text(reply: BaseMessage) -> str:
    text = getattr(reply, "text", None)
    return text if isinstance(text, str) else str(reply.content)


async def _call[T: BaseModel](
    method: Method,
    model: BaseChatModel,
    schema: type[T],
    system: str,
    extra: list[BaseMessage],
    user: str,
    config: RunnableConfig | None,
) -> T:
    if method == "json_mode":
        instruction = (
            "Reply with ONLY one JSON object, no prose and no code fences, that matches this "
            f"JSON Schema:\n{json.dumps(schema.model_json_schema())}"
        )
        messages: list[BaseMessage] = [
            SystemMessage(content=f"{system}\n\n{instruction}"),
            HumanMessage(content=user),
            *extra,
        ]
        reply = await model.ainvoke(messages, config=config)
        return schema.model_validate_json(extract_json(_reply_text(reply)))

    runnable = (
        model.with_structured_output(schema)
        if method == "native"
        else model.with_structured_output(schema, method="function_calling")
    )
    messages = [SystemMessage(content=system), HumanMessage(content=user), *extra]
    result = await runnable.ainvoke(messages, config=config)
    return result if isinstance(result, schema) else schema.model_validate(result)


async def ainvoke_structured[T: BaseModel](
    model: BaseChatModel,
    schema: type[T],
    system: str,
    user: str,
    config: RunnableConfig | None = None,
    methods: Sequence[Method] = DEFAULT_METHODS,
) -> T:
    extra: list[BaseMessage] = []
    failures = 0
    last_error: Exception | None = None
    for method in methods:
        while True:
            try:
                return await _call(method, model, schema, system, extra, user, config)
            except (ValidationError, ValueError, TypeError) as exc:
                last_error = exc
                failures += 1
                if failures >= MAX_VALIDATION_ATTEMPTS:
                    raise StructuredOutputError(
                        f"no valid {schema.__name__} after retry: {last_error}"
                    ) from exc
                extra.append(
                    HumanMessage(
                        content=f"Your previous reply was invalid ({exc}). "
                        "Reply again with output that matches the schema exactly."
                    )
                )
            except Exception as exc:
                if _is_capability_error(exc):
                    break  # this method is unsupported here; try the next one
                raise
    raise StructuredOutputError(f"no supported structured-output method for {schema.__name__}")
