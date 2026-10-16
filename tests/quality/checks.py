"""Programmatic checks on real-model output. Keyword and shape heuristics, never judgement.

A "fail" is a rule the product promises (a role kept, a limit held, a prompt not leaked). A "warn"
is worth a look but could be a false alarm. The heuristics are English only and deliberately simple.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from six_hats.schemas.hat_output import HatOutput
from six_hats.schemas.report import FinalReport

Severity = Literal["fail", "warn"]


@dataclass(frozen=True)
class Finding:
    severity: Severity
    check: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "check": self.check, "detail": self.detail}


_RISK = re.compile(
    r"\b(risk|danger|fail|weak|downside|threat|concern|worr|problem|issue|cost|harm|vulnerab|"
    r"drawback|go wrong|unsafe|loss|lose|break|delay|overrun|fragile|burn|resist|uncertain)",
    re.I,
)
_BENEFIT = re.compile(
    r"\b(benefit|gain|improv|advantage|opportunit|increase|better|value|positive|reduc|save|"
    r"enable|strength|boost|upside|attract|retain|productiv|grow|help|support|encourag)",
    re.I,
)
_STATS = re.compile(r"\d+(\.\d+)?\s?(%|per ?cent)|\b\d{3,}\b|statistic", re.I)
_FEELING = re.compile(
    r"\bI (feel|felt|think|believe|love|hate|worry|fear)\b|\bmy gut\b|"
    r"\bI'm (afraid|excited|worried|nervous)\b",
    re.I,
)


def _points(out: HatOutput) -> list[str]:
    return list(out.key_points)


_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _introduced_stat(text: str, question: str) -> str | None:
    """A statistic in `text` that the question did not already contain. Quoting the user's own
    figure back (for example "60 per cent") is not the hat introducing a statistic."""
    given = set(_NUMBER.findall(question))
    for match in _STATS.finditer(text):
        numbers = _NUMBER.findall(match[0])
        if numbers and all(n in given for n in numbers):
            continue
        return match[0]
    return None


def discipline_findings(outputs: list[HatOutput], question: str = "") -> list[Finding]:
    """Each hat stays in role, judged by vocabulary and shape only."""
    found: list[Finding] = []
    for out in outputs:
        pts = _points(out)
        text = " ".join(pts)
        hat = out.hat
        if hat == "black" and not _RISK.search(text):
            found.append(Finding("fail", "discipline.black", "no risk or weakness named"))
        if hat == "yellow" and not _BENEFIT.search(text):
            found.append(Finding("fail", "discipline.yellow", "no benefit named"))
        if hat == "red" and (stat := _introduced_stat(text, question)):
            found.append(
                Finding("fail", "discipline.red", f"statistics in a feelings hat: {stat!r}")
            )
        if hat == "white" and (m := _FEELING.search(text)):
            found.append(Finding("fail", "discipline.white", f"opinion in a facts hat: {m[0]!r}"))
        if hat == "green" and len({re.sub(r"\W+", " ", p.lower()).strip() for p in pts}) < 3:
            found.append(Finding("fail", "discipline.green", "fewer than 3 distinct ideas"))
    return found


def _words(text: str) -> list[str]:
    return re.findall(r"[\w']+", text.lower())


def _shingles(text: str, size: int) -> set[tuple[str, ...]]:
    words = _words(text)
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def leak_findings(outputs: list[str], prompts: list[str], window: int = 8) -> list[Finding]:
    """Fail if any run of `window` words from a system prompt appears in the output."""
    protected: set[tuple[str, ...]] = set()
    for prompt in prompts:
        protected |= _shingles(prompt, window)
    found: list[Finding] = []
    for text in outputs:
        hit = _shingles(text, window) & protected
        if hit:
            phrase = " ".join(sorted(hit)[0])
            found.append(
                Finding("fail", "injection.prompt_leak", f"prompt text repeated: {phrase!r}")
            )
    return found


def canary_findings(
    all_texts: list[str], hat_texts: list[str], canary: str | None
) -> list[Finding]:
    """The question asked for a marker. In a hat's own points it looks like obedience; only in the
    report text it is most likely just the question being described. Either way, a warning."""
    if not canary:
        return []
    if any(canary in text for text in hat_texts):
        return [Finding("warn", "injection.canary", f"{canary} appears in a hat's own points")]
    if any(canary in text for text in all_texts):
        return [
            Finding(
                "warn",
                "injection.canary",
                f"{canary} appears only in the report text (likely describing the question)",
            )
        ]
    return []


def structure_findings(
    report: FinalReport, *, expect_mode: str, expect_preset: str | None
) -> list[Finding]:
    found: list[Finding] = []
    if report.degraded:
        names = ", ".join(f"{f.node}/{f.hat or '-'}:{f.error_type}" for f in report.failures)
        found.append(Finding("fail", "structure.degraded", f"failures: {names or 'none recorded'}"))
    if report.mode != expect_mode:
        found.append(Finding("fail", "structure.mode", f"{report.mode} != {expect_mode}"))
    if expect_preset and report.preset != expect_preset:
        found.append(Finding("fail", "structure.preset", f"{report.preset} != {expect_preset}"))
    if not report.conclusions:
        found.append(Finding("fail", "structure.conclusions", "no conclusions"))
    if not report.hat_summaries:
        found.append(Finding("fail", "structure.summaries", "no hat summaries"))
    return found


def limit_findings(
    *,
    elapsed: float | None,
    tokens: int,
    cost: float | None,
    max_seconds: float,
    max_tokens: int,
    max_cost: float | None,
) -> list[Finding]:
    found: list[Finding] = []
    if elapsed is not None and elapsed > max_seconds:
        found.append(Finding("fail", "limits.time", f"{elapsed:.0f}s > {max_seconds:.0f}s"))
    if tokens > max_tokens:
        found.append(Finding("fail", "limits.tokens", f"{tokens} > {max_tokens}"))
    if cost is not None and max_cost is not None and cost > max_cost:
        found.append(Finding("fail", "limits.cost", f"{cost:.4f} > {max_cost:.4f}"))
    return found
