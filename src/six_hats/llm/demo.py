"""An offline demo model: no key, no network, no cost. For trying the app and the UI.

It does not think. It returns fixed, clearly labelled text shaped like real output, so every part of
the workflow (framing, hats, progress, report, cost line) can be exercised. Select it with
`SIXHATS_LLM__PROVIDER=demo`. Its output is never meant to be read as advice.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

_HAT = re.compile(r"You are the (\w+) HAT")
_HATS = ("white", "red", "green", "yellow", "black")
_TAG = "[demo output, not from a model]"


def _framing() -> dict[str, Any]:
    return {
        "focus": f"The question as asked. {_TAG}",
        "objective": "Explore it from every angle.",
        "thinking_type": "evaluation",
        "mode": "parallel",
        "sequence": list(_HATS),
        "rationale": "Demo framing: all five hats, in parallel.",
    }


def _hat(name: str) -> dict[str, Any]:
    return {
        "hat": name,
        "key_points": [f"{name} point {i} {_TAG}" for i in (1, 2, 3)],
        "confidence": "medium",
    }


def _close() -> dict[str, Any]:
    return {
        "framing_summary": f"A demo run, so nothing here is real analysis. {_TAG}",
        "hat_summaries": [{"hat": h, "summary": f"{h} demo summary"} for h in _HATS],
        "conclusions": [f"This is the demo model talking. {_TAG}"],
        "agreements": ["The workflow ran end to end."],
        "tensions": ["Demo text cannot be weighed against anything."],
        "recommended_next_steps": ["Switch to a real model: SIXHATS_LLM__PROVIDER=anthropic."],
        "open_questions": ["What would a real model say?"],
    }


def _checkpoint() -> dict[str, Any]:
    return {
        "progress": [f"The hats so far have each added a view. {_TAG}"],
        "gaps": ["Nothing real was analysed: this is the demo model."],
        "next_focus": f"Carry on with the next hat. {_TAG}",
    }


def _reply(system: str) -> dict[str, Any]:
    if "BlueCheckpoint" in system:
        return _checkpoint()
    if "BlueCloseOutput" in system:
        return _close()
    if '"Framing"' in system:
        return _framing()
    match = _HAT.search(system)
    return _hat(match.group(1).lower() if match else "white")


class DemoChatModel(BaseChatModel):
    delay: float = 0.3  # a short pause so progress is visible

    @property
    def _llm_type(self) -> str:
        return "demo"

    def _result(self, messages: list[BaseMessage]) -> ChatResult:
        system = str(messages[0].content) if messages else ""
        size = sum(len(str(m.content)) for m in messages)
        body = json.dumps(_reply(system))
        msg = AIMessage(
            content=body,
            usage_metadata={
                "input_tokens": size // 4,
                "output_tokens": len(body) // 4,
                "total_tokens": (size + len(body)) // 4,
            },
            response_metadata={"model_name": "demo"},
        )
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._result(messages)

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        await asyncio.sleep(self.delay)
        return self._result(messages)
