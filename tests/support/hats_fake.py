"""A scripted chat model that answers by schema and hat, and records every call."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from typing import Any

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel

from six_hats.schemas.framing import Framing
from six_hats.schemas.hat_output import HatOutput
from six_hats.schemas.report import BlueCloseOutput, HatSummary

Responder = Callable[[str, str, list[BaseMessage]], Any]
_HAT = re.compile(r"You are the (\w+) HAT")


def default_framing() -> Framing:
    return Framing(
        focus="Whether to adopt a four-day week.",
        objective="Decide with balanced thinking.",
        thinking_type="evaluation",
        mode="parallel",
        sequence=["white", "red", "green", "yellow", "black"],
        rationale="An existing proposal to judge.",
    )


def default_response(kind: str, hat: str, _messages: list[BaseMessage]) -> Any:
    if kind == "Framing":
        return default_framing()
    if kind == "HatOutput":
        return HatOutput(hat=hat, key_points=[f"{hat} point {i}" for i in range(3)])  # type: ignore[arg-type]
    if kind == "BlueCloseOutput":
        return BlueCloseOutput(
            framing_summary="A four-day week was examined.",
            hat_summaries=[
                HatSummary(hat=h, summary=f"{h} summary")  # type: ignore[arg-type]
                for h in ("white", "red", "green", "yellow", "black")
            ],
            conclusions=["Pilot it first (Black, Yellow)."],
            agreements=["A pilot reduces risk."],
            tensions=["Cost certainty versus staff morale."],
            recommended_next_steps=["Run a 3-month pilot."],
            open_questions=["What do competitors do?"],
        )
    raise AssertionError(kind)


class HatsFakeModel(GenericFakeChatModel):
    """Answers with_structured_output(schema) calls. `calls` holds (kind, hat, user_text)."""

    responder: Responder = default_response
    calls: list[tuple[str, str, str]] = []
    delay: float = 0.01

    def with_structured_output(self, schema: Any, **_: Any) -> Runnable[Any, Any]:
        kind = schema.__name__

        async def _answer(messages: list[BaseMessage]) -> BaseModel:
            system, user = str(messages[0].content), str(messages[1].content)
            match = _HAT.search(system)
            hat = match.group(1).lower() if match else kind
            self.calls.append((kind, hat, user))
            await asyncio.sleep(self.delay)  # lets parallel hats genuinely overlap
            result = self.responder(kind, hat, messages)
            if isinstance(result, Exception):
                raise result
            return result  # type: ignore[no-any-return]

        return RunnableLambda(lambda _m: None, afunc=_answer)


def make_hats_fake(responder: Responder = default_response) -> HatsFakeModel:
    return HatsFakeModel(messages=iter([AIMessage(content="x")]), responder=responder, calls=[])
