"""Graph nodes. All are async so per-node timeouts can be added in phase 4."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any, Protocol

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from six_hats.graph.state import GraphState
from six_hats.hats.base import brief_block, data_block, load_prompt, run_hat
from six_hats.llm.structured import ainvoke_structured
from six_hats.observability.logging import get_logger
from six_hats.schemas.framing import Framing
from six_hats.schemas.hat_output import THINKING_HATS, ThinkingHatName
from six_hats.schemas.report import BlueCloseOutput, FinalReport, HatSummary
from six_hats.security.input_validation import validate_request

ModelResolver = Callable[[str], BaseChatModel]


class Node(Protocol):
    async def __call__(self, state: GraphState, config: RunnableConfig) -> dict[str, Any]: ...


_log = get_logger()


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def make_intake(max_chars: int) -> Node:
    async def intake(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
        question = validate_request(state.get("question", ""), max_chars)
        _log.info("node.completed", node="intake", run_id=state.get("run_id"))
        return {"question": question}

    return intake


def make_blue_open(resolve: ModelResolver) -> Node:
    async def blue_open(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
        start = time.perf_counter()
        prompt = load_prompt("blue_open")
        framing = await ainvoke_structured(
            resolve("blue_open"),
            Framing,
            prompt.text,
            data_block("question", state["question"]),
            config=config,
        )
        _log.info(
            "framing.completed",
            run_id=state["run_id"],
            mode=framing.mode,
            sequence=framing.sequence,
            source="model",
            duration_ms=_ms(start),
        )
        return {"framing": framing}

    return blue_open


def make_hat(hat: ThinkingHatName, resolve: ModelResolver) -> Node:
    async def hat_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
        start = time.perf_counter()
        output = await run_hat(hat, resolve(hat), state["question"], state["framing"], config)
        _log.info(
            "node.completed",
            node=hat,
            hat=hat,
            run_id=state["run_id"],
            prompt_version=load_prompt(hat).version,
            duration_ms=_ms(start),
        )
        return {"outputs": {hat: output}}

    return hat_node


def make_blue_close(resolve: ModelResolver) -> Node:
    async def blue_close(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
        start = time.perf_counter()
        outputs = state.get("outputs", {})
        missing = [h for h in THINKING_HATS if h not in outputs]
        hat_outputs = json.dumps(
            {h: o.model_dump(exclude={"hat"}) for h, o in outputs.items()}, indent=2
        )
        user = "\n\n".join(
            [
                data_block("question", state["question"]),
                brief_block(state["framing"]),
                data_block("hat_outputs", hat_outputs),
                data_block("missing_hats", ", ".join(missing) or "none"),
            ]
        )
        prompt = load_prompt("blue_close")
        closing = await ainvoke_structured(
            resolve("blue_close"), BlueCloseOutput, prompt.text, user, config=config
        )
        report = _assemble_report(state["run_id"], closing, missing, state)
        _log.info(
            "node.completed",
            node="blue_close",
            run_id=state["run_id"],
            degraded=report.degraded,
            duration_ms=_ms(start),
        )
        return {"report": report}

    return blue_close


def _assemble_report(
    run_id: str, closing: BlueCloseOutput, missing: list[ThinkingHatName], state: GraphState
) -> FinalReport:
    """Metadata comes from code, never from the model."""
    present = set(state.get("outputs", {}))
    summaries = [s for s in closing.hat_summaries if s.hat in present]
    seen: set[str] = set()
    unique: list[HatSummary] = []
    for summary in summaries:
        if summary.hat not in seen:
            seen.add(summary.hat)
            unique.append(summary)
    versions = {name: load_prompt(name).version for name in _PROMPTS_USED}  # type: ignore[arg-type]
    return FinalReport(
        run_id=run_id,
        framing_summary=closing.framing_summary,
        hat_summaries=unique,
        conclusions=closing.conclusions,
        agreements=closing.agreements,
        tensions=closing.tensions,
        recommended_next_steps=closing.recommended_next_steps,
        open_questions=closing.open_questions,
        missing_perspectives=missing,
        degraded=bool(missing or state.get("failures")),
        prompt_versions=versions,
    )


_PROMPTS_USED = (*THINKING_HATS, "blue_open", "blue_close")
