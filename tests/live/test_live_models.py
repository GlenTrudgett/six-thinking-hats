"""Live checks against a real model. Skipped unless you opt in.

Local OpenAI-compatible server (llama.cpp, Ollama, ...):
    SIXHATS_LIVE=1 SIXHATS_LLM__PROVIDER=local SIXHATS_LLM__MODEL=<model name> \\
    SIXHATS_LLM__LOCAL__BASE_URL=http://127.0.0.1:8080/v1 \\
    uv run pytest tests/live -m live --no-cov -s

Anthropic:
    SIXHATS_LIVE=1 SIXHATS_LLM__PROVIDER=anthropic SIXHATS_LLM__ANTHROPIC_API_KEY=<key> \\
    uv run pytest tests/live -m live --no-cov -s
"""

from __future__ import annotations

import os

import pytest

from six_hats.config.settings import load_settings
from six_hats.hats.base import run_hat
from six_hats.llm.factory import create_model
from six_hats.schemas.hat_output import HatOutput
from tests.support.hats_fake import default_framing

pytestmark = [
    pytest.mark.live,
    pytest.mark.enable_socket,
    pytest.mark.skipif(os.environ.get("SIXHATS_LIVE") != "1", reason="set SIXHATS_LIVE=1 to run"),
]

QUESTION = "Should a small company move from a five-day to a four-day work week?"


@pytest.mark.parametrize("hat", ["white", "red"])
async def test_single_hat_against_configured_model(hat):
    settings = load_settings()
    model = create_model(settings.llm)
    out = await run_hat(hat, model, QUESTION, default_framing())
    print(f"\n[{settings.llm.provider}/{settings.llm.model}] {hat}: {out.key_points}")
    assert isinstance(out, HatOutput) and out.hat == hat
    assert 3 <= len(out.key_points) <= 7


async def test_full_workflow_against_configured_model():
    from six_hats.graph.runner import run_workflow

    settings = load_settings()
    model = create_model(settings.llm)
    report = await run_workflow(QUESTION, lambda _n: model, run_id="live")
    print(f"\nconclusions: {report.conclusions}\nmissing: {report.missing_perspectives}")
    assert report.conclusions and not report.missing_perspectives
