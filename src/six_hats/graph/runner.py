"""Runs the graph. Streams updates only, so private state channels are never exposed."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.runnables import RunnableConfig

from six_hats.graph.builder import build_graph
from six_hats.graph.nodes import ModelResolver
from six_hats.graph.resilience import DEFAULT_LIMITS, Limits
from six_hats.observability.logging import get_logger
from six_hats.schemas.presets import SequenceOverride
from six_hats.schemas.report import FinalReport

_log = get_logger()


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


ProgressCallback = Callable[[str, str], None]  # (node, message)


def estimate_cost(
    totals: dict[str, int], price_in: float | None, price_out: float | None
) -> float | None:
    """Cost from token totals and per-million-token prices; None unless both prices are set."""
    if price_in is None or price_out is None:
        return None
    return (totals["input_tokens"] * price_in + totals["output_tokens"] * price_out) / 1_000_000


def _describe(node: str, delta: Any) -> str:
    if node == "blue_open" and isinstance(delta, dict) and delta.get("framing") is not None:
        f = delta["framing"]
        return f"framed ({f.mode}: {', '.join(f.sequence)})"
    if isinstance(delta, dict) and isinstance(delta.get("outputs"), dict):
        return "done: " + ", ".join(sorted(delta["outputs"]))
    if isinstance(delta, dict) and delta.get("failures"):
        return "failed (see report)"
    return "done"


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
    override: SequenceOverride | None = None,
    on_progress: ProgressCallback | None = None,
    price_input_per_mtok: float | None = None,
    price_output_per_mtok: float | None = None,
    price_currency: str | None = None,
) -> FinalReport:
    rid = run_id or new_run_id()
    graph = build_graph(resolve, max_question_chars=max_question_chars, limits=limits)
    usage = UsageMetadataCallbackHandler()
    config: RunnableConfig = {"callbacks": [usage], "recursion_limit": recursion_limit}
    _log.info("run.started", run_id=rid)
    started = time.monotonic()

    report: FinalReport | None = None
    async for update in graph.astream(
        {"run_id": rid, "question": question, "override": override}, config, stream_mode="updates"
    ):
        for node, delta in update.items():
            keys = sorted(delta) if isinstance(delta, dict) else []
            _log.debug("graph.update", run_id=rid, node=node, keys=keys)
            if on_progress is not None:
                on_progress(node, _describe(node, delta))
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
    elapsed = round(time.monotonic() - started, 2)
    cost = (
        estimate_cost(totals, price_input_per_mtok, price_output_per_mtok)
        if price_currency
        else None  # a cost without a currency would be ambiguous, so none is shown
    )
    report = report.model_copy(
        update={
            "models_used": sorted(models),
            "token_usage": totals,
            "elapsed_seconds": elapsed,
            "estimated_cost": None if cost is None else round(cost, 6),
            "cost_currency": price_currency if cost is not None else None,
        }
    )
    _log.info(
        "run.completed",
        run_id=rid,
        degraded=report.degraded,
        tokens_in=totals["input_tokens"],
        tokens_out=totals["output_tokens"],
    )
    return report
