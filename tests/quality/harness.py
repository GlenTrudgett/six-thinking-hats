"""Run the fixed questions against a model and record what happened, as JSON."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from six_hats.graph.builder import build_graph
from six_hats.graph.resilience import DEFAULT_LIMITS, Limits
from six_hats.graph.runner import estimate_cost
from six_hats.hats.base import load_prompt
from six_hats.schemas.hat_output import HatOutput
from six_hats.schemas.presets import SequenceOverride
from six_hats.schemas.report import FinalReport
from tests.quality import checks

QUESTIONS_FILE = Path(__file__).with_name("questions.yaml")
RESULTS_DIR = Path("quality-results")


class Question(BaseModel):
    id: str
    text: str
    force: dict[str, str]
    discipline: bool = True
    canary: str | None = None

    def override(self) -> SequenceOverride:
        if self.force.get("mode") == "parallel":
            return SequenceOverride(parallel=True)
        return SequenceOverride.model_validate({"preset": self.force["preset"]})

    @property
    def expect_mode(self) -> str:
        return "parallel" if self.force.get("mode") == "parallel" else "sequential"

    @property
    def expect_preset(self) -> str | None:
        return self.force.get("preset")


class Thresholds(BaseModel):
    max_seconds: float = 240.0
    max_tokens: int = 80_000
    max_cost: float | None = None  # per question, in the price currency


class Prices(BaseModel):
    input_per_mtok: float | None = None
    output_per_mtok: float | None = None
    currency: str | None = None


def load_questions(limit: int | None = None) -> list[Question]:
    data = yaml.safe_load(QUESTIONS_FILE.read_text(encoding="utf-8"))
    questions = [Question.model_validate(item) for item in data]
    ids = [q.id for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate question ids")
    return questions[:limit] if limit else questions


def prompt_corpus() -> list[str]:
    """Every system prompt, as the model sees it, for the leak check."""
    from six_hats.schemas.presets import describe_presets

    names = (
        "white",
        "red",
        "green",
        "yellow",
        "black",
        "blue_open",
        "blue_close",
        "blue_checkpoint",
    )
    texts = []
    for name in names:
        try:
            text = load_prompt(name).text  # type: ignore[arg-type]
        except FileNotFoundError:
            continue  # a prompt that does not exist on this version
        texts.append(text.replace("{{presets}}", describe_presets()))
    return texts


@dataclass
class QuestionResult:
    id: str
    findings: list[checks.Finding] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    elapsed_seconds: float = 0.0
    cost: float | None = None
    hats: list[dict[str, Any]] = field(default_factory=list)
    prompt_versions: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    judge: dict[str, Any] | None = None

    @property
    def failures(self) -> list[checks.Finding]:
        return [f for f in self.findings if f.severity == "fail"]

    @property
    def ok(self) -> bool:
        return self.error is None and not self.failures

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ok": self.ok,
            "error": self.error,
            "findings": [f.as_dict() for f in self.findings],
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "elapsed_seconds": self.elapsed_seconds,
            "cost": self.cost,
            "prompt_versions": self.prompt_versions,
            "hats": self.hats,
            "judge": self.judge,
        }


def _usage(handler: UsageMetadataCallbackHandler) -> tuple[int, int]:
    tin = tout = 0
    for meta in handler.usage_metadata.values():
        data = dict(meta)
        tin += int(data.get("input_tokens", 0))
        tout += int(data.get("output_tokens", 0))
    return tin, tout


async def run_question(
    q: Question,
    model: BaseChatModel,
    *,
    limits: Limits = DEFAULT_LIMITS,
    prices: Prices | None = None,
    thresholds: Thresholds | None = None,
) -> QuestionResult:
    """Run one question through the real graph and apply every programmatic check."""
    prices = prices or Prices()
    thresholds = thresholds or Thresholds()
    result = QuestionResult(id=q.id)
    usage = UsageMetadataCallbackHandler()
    config: RunnableConfig = {"callbacks": [usage], "recursion_limit": 25}
    graph = build_graph(lambda _n: model, limits=limits)
    outputs: list[HatOutput] = []
    keyed: list[tuple[str, HatOutput]] = []
    report: FinalReport | None = None
    started = time.monotonic()
    try:
        async for update in graph.astream(
            {"run_id": f"q-{q.id}", "question": q.text, "override": q.override()},
            config,
            stream_mode="updates",
        ):
            for node, delta in update.items():
                if not isinstance(delta, dict):
                    continue
                if node == "blue_close":
                    report = delta["report"]
                elif isinstance(delta.get("outputs"), dict):
                    for key, out in delta["outputs"].items():
                        keyed.append((key, out))
                        outputs.append(out)
    except Exception as exc:  # a crash is a finding, not a reason to stop the suite
        result.error = f"{type(exc).__name__}: {exc}"[:300]
    result.elapsed_seconds = round(time.monotonic() - started, 2)
    result.tokens_in, result.tokens_out = _usage(usage)
    if prices.currency:
        result.cost = estimate_cost(
            {"input_tokens": result.tokens_in, "output_tokens": result.tokens_out},
            prices.input_per_mtok,
            prices.output_per_mtok,
        )
    result.hats = [{"step": k, "hat": o.hat, "key_points": list(o.key_points)} for k, o in keyed]
    if report is None:
        return result

    result.prompt_versions = dict(report.prompt_versions)
    hat_texts = [p for o in outputs for p in (*o.key_points, *o.assumptions, *o.open_questions)]
    texts = list(hat_texts)
    texts += [report.framing_summary, *report.conclusions, *report.agreements, *report.tensions]
    texts += [*report.recommended_next_steps, *report.open_questions]
    texts += [s.summary for s in report.hat_summaries]
    found = checks.structure_findings(
        report, expect_mode=q.expect_mode, expect_preset=q.expect_preset
    )
    if q.discipline:
        found += checks.discipline_findings(outputs, q.text)
    found += checks.leak_findings(texts, prompt_corpus())
    found += checks.canary_findings(texts, hat_texts, q.canary)
    found += checks.limit_findings(
        elapsed=result.elapsed_seconds,
        tokens=result.tokens_in + result.tokens_out,
        cost=result.cost,
        max_seconds=thresholds.max_seconds,
        max_tokens=thresholds.max_tokens,
        max_cost=thresholds.max_cost,
    )
    result.findings = found
    return result


@dataclass
class Recorder:
    """Collects results, enforces a spending cap, and writes one JSON file per run."""

    provider: str
    model: str
    currency: str | None = None
    budget: float | None = None
    judge_model: str | None = None
    results: list[QuestionResult] = field(default_factory=list)
    spent: float = 0.0
    started: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def exceeded(self) -> bool:
        return self.budget is not None and self.spent >= self.budget

    def add(self, result: QuestionResult, extra_cost: float | None = None) -> None:
        self.results.append(result)
        self.spent += (result.cost or 0.0) + (extra_cost or 0.0)

    def as_dict(self) -> dict[str, Any]:
        done = self.results
        return {
            "started": self.started.isoformat(timespec="seconds"),
            "provider": self.provider,
            "model": self.model,
            "judge_model": self.judge_model,
            "currency": self.currency,
            "budget": self.budget,
            "spent": round(self.spent, 6),
            "passed": sum(r.ok for r in done),
            "failed": sum(not r.ok for r in done),
            "questions": [r.as_dict() for r in done],
        }

    def write(self, directory: Path = RESULTS_DIR) -> Path | None:
        if not self.results:
            return None
        directory.mkdir(parents=True, exist_ok=True)
        stamp = self.started.strftime("%Y%m%dT%H%M%SZ")
        safe = "".join(c if c.isalnum() or c in "-._" else "_" for c in self.model)
        path = directory / f"{stamp}-{self.provider}-{safe}.json"
        path.write_text(json.dumps(self.as_dict(), indent=2) + "\n", encoding="utf-8")
        return path


__all__ = [
    "Prices",
    "Question",
    "QuestionResult",
    "Recorder",
    "Thresholds",
    "load_questions",
    "prompt_corpus",
    "run_question",
]
