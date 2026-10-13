"""Behavioural checks on a real model. Skipped unless you opt in; spends real money on Claude.

    make quality                 # programmatic checks only
    make quality-judge           # plus the judge scores (a second model call per question)

Settings (environment or .env):
    SIXHATS_QUALITY_LIMIT=3          run only the first N questions
    SIXHATS_QUALITY_BUDGET=1.50      stop when this much is spent (needs the three price settings)
    SIXHATS_QUALITY_MAX_SECONDS=240  per-question time limit
    SIXHATS_QUALITY_MAX_TOKENS=80000 per-question token limit
    SIXHATS_QUALITY_MAX_COST=0.50    per-question cost limit (needs prices)
    SIXHATS_QUALITY_JUDGE=1          also score each hat with a judge model
    SIXHATS_QUALITY_JUDGE_MODEL=...  the judge model (default: the model under test)

Results are written to quality-results/<time>-<provider>-<model>.json (not committed).
"""

from __future__ import annotations

import os

import pytest
from langchain_core.callbacks import UsageMetadataCallbackHandler

from six_hats.config.settings import load_settings
from six_hats.graph.resilience import Limits
from six_hats.graph.runner import estimate_cost
from six_hats.llm.factory import create_model
from tests.quality.harness import (
    Prices,
    Recorder,
    Thresholds,
    load_questions,
    run_question,
)
from tests.quality.judge import judge_question

pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.quality,
    pytest.mark.enable_socket,
    pytest.mark.skipif(
        os.environ.get("SIXHATS_QUALITY") != "1", reason="set SIXHATS_QUALITY=1 to run"
    ),
]


def _env_float(name: str) -> float | None:
    value = os.environ.get(name)
    return float(value) if value else None


def _limit() -> int | None:
    value = os.environ.get("SIXHATS_QUALITY_LIMIT")
    return int(value) if value else None


QUESTIONS = load_questions(_limit())


@pytest.fixture(scope="module")
def settings():
    return load_settings()


@pytest.fixture(scope="module")
def recorder(settings):
    run = settings.run
    rec = Recorder(
        provider=settings.llm.provider,
        model=settings.llm.model,
        currency=run.price_currency,
        budget=_env_float("SIXHATS_QUALITY_BUDGET"),
        judge_model=(
            os.environ.get("SIXHATS_QUALITY_JUDGE_MODEL", settings.llm.model)
            if os.environ.get("SIXHATS_QUALITY_JUDGE") == "1"
            else None
        ),
    )
    if rec.budget is not None and not run.price_currency:
        pytest.fail("SIXHATS_QUALITY_BUDGET needs the three price settings (see .env.example)")
    yield rec
    path = rec.write()
    if path:
        print(
            f"\nresults: {path}  passed={rec.as_dict()['passed']} failed={rec.as_dict()['failed']}"
        )


@pytest.mark.parametrize("question", QUESTIONS, ids=lambda q: q.id)
async def test_question(question, settings, recorder):
    if recorder.exceeded:
        pytest.skip(f"budget used up ({recorder.spent:.4f} {recorder.currency})")
    run = settings.run
    model = create_model(settings.llm)
    result = await run_question(
        question,
        model,
        limits=Limits(
            node_timeout_seconds=run.node_timeout_seconds,
            node_retries=run.node_retries,
            retry_backoff_seconds=run.retry_backoff_seconds,
            max_context_chars=run.max_context_chars,
        ),
        prices=Prices(
            input_per_mtok=run.price_input_per_mtok,
            output_per_mtok=run.price_output_per_mtok,
            currency=run.price_currency,
        ),
        thresholds=Thresholds(
            max_seconds=_env_float("SIXHATS_QUALITY_MAX_SECONDS") or 240.0,
            max_tokens=int(os.environ.get("SIXHATS_QUALITY_MAX_TOKENS", "80000")),
            max_cost=_env_float("SIXHATS_QUALITY_MAX_COST"),
        ),
    )
    judge_cost = None
    if recorder.judge_model and result.hats:
        judge_llm = create_model(settings.llm.model_copy(update={"model": recorder.judge_model}))
        usage = UsageMetadataCallbackHandler()
        try:
            result.judge = await judge_question(
                judge_llm, question.text, result.hats, {"callbacks": [usage]}
            )
        except Exception as exc:  # a judge failure never fails the question
            result.judge = {"error": f"{type(exc).__name__}: {exc}"[:300]}
        totals = {"input_tokens": 0, "output_tokens": 0}
        for meta in usage.usage_metadata.values():
            totals["input_tokens"] += int(dict(meta).get("input_tokens", 0))
            totals["output_tokens"] += int(dict(meta).get("output_tokens", 0))
        if run.price_currency:
            judge_cost = estimate_cost(totals, run.price_input_per_mtok, run.price_output_per_mtok)
    recorder.add(result, extra_cost=judge_cost)

    for finding in result.findings:
        print(f"  [{finding.severity}] {question.id}: {finding.check}: {finding.detail}")
    assert result.error is None, result.error
    assert not result.failures, "; ".join(f"{f.check}: {f.detail}" for f in result.failures)
