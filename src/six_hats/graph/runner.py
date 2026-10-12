"""Runs the graph. Streams updates only, so private state channels are never exposed."""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.runnables import RunnableConfig

from six_hats.graph.builder import build_graph
from six_hats.graph.nodes import ModelResolver
from six_hats.graph.resilience import DEFAULT_LIMITS, Limits
from six_hats.observability.logging import get_logger
from six_hats.schemas.report import FinalReport

_log = get_logger()


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


class RunError(RuntimeError):
    """The graph finished without producing a report."""


async def run_workflow(
    question: str,
    resolve: ModelResolver,
    *,
    run_id: str | None = None,
    max_question_chars: int = 4000,
    recursion_limit: int = 25,
    limits: Limits = DEFAULT_LIMITS,
) -> FinalReport:
    rid = run_id or new_run_id()
    graph = build_graph(resolve, max_question_chars=max_question_chars, limits=limits)
    usage = UsageMetadataCallbackHandler()
    config: RunnableConfig = {"callbacks": [usage], "recursion_limit": recursion_limit}
    _log.info("run.started", run_id=rid)

    report: FinalReport | None = None
    async for update in graph.astream(
        {"run_id": rid, "question": question}, config, stream_mode="updates"
    ):
        for node, delta in update.items():
            keys = sorted(delta) if isinstance(delta, dict) else []
            _log.debug("graph.update", run_id=rid, node=node, keys=keys)
            if node == "blue_close" and isinstance(delta, dict):
                report = delta["report"]
    if report is None:
        raise RunError(f"run {rid} produced no report")

    totals: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    models: list[str] = []
    for model_name, meta in usage.usage_metadata.items():
        models.append(model_name)
        data: dict[str, Any] = dict(meta)
        for key in totals:
            totals[key] += int(data.get(key, 0))
    report = report.model_copy(update={"models_used": sorted(models), "token_usage": totals})
    _log.info(
        "run.completed",
        run_id=rid,
        degraded=report.degraded,
        tokens_in=totals["input_tokens"],
        tokens_out=totals["output_tokens"],
    )
    return report
