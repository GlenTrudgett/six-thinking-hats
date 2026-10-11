"""Deterministic fake chat model: returns queued items from with_structured_output."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableLambda


class FakeStructuredModel(GenericFakeChatModel):
    """Each ainvoke on the structured runnable pops the next queued response."""

    queue: list[Any] = []
    calls: int = 0

    def with_structured_output(self, schema: Any, **_: Any) -> Runnable[Any, Any]:
        async def _next(_messages: Any) -> Any:
            self.calls += 1
            item = self.queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        return RunnableLambda(lambda _m: None, afunc=_next)


def make_fake(*items: Any) -> FakeStructuredModel:
    return FakeStructuredModel(messages=iter([AIMessage(content="x")]), queue=list(items))
