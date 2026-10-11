"""Get schema-valid output from any chat model, with one bounded repair retry."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError


class StructuredOutputError(RuntimeError):
    pass


async def ainvoke_structured[T: BaseModel](
    model: BaseChatModel, schema: type[T], system: str, user: str
) -> T:
    runnable = model.with_structured_output(schema)
    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    last_error: Exception | None = None
    for attempt in range(2):
        if attempt:
            messages.append(
                HumanMessage(
                    content=f"Your previous reply was invalid ({last_error}). "
                    "Reply again with output that matches the schema exactly."
                )
            )
        try:
            result = await runnable.ainvoke(messages)
            if isinstance(result, schema):
                return result
            return schema.model_validate(result)
        except (ValidationError, ValueError, TypeError) as exc:
            last_error = exc
    raise StructuredOutputError(f"no valid {schema.__name__} after retry: {last_error}")
