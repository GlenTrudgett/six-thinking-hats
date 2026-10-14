"""Summarise and compare result files.

    uv run python -m tests.quality.compare quality-results/a.json quality-results/b.json

Prints mean judge scores per hat for each file, with the model and prompt versions beside them,
so two prompt versions or two models can be set side by side.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

CRITERIA = ("stays_in_role", "specific_to_question", "adds_new_content")


def summarise(result: dict[str, Any]) -> dict[str, Any]:
    """Mean score per hat and criterion, plus pass counts and cost, from one results file."""
    totals: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    versions: dict[str, str] = {}
    for q in result.get("questions", []):
        versions.update(q.get("prompt_versions") or {})
        for s in (q.get("judge") or {}).get("scores", []):
            for c in CRITERIA:
                totals[s["hat"]][c].append(s[c])
    means = {
        hat: {c: round(sum(v) / len(v), 2) for c, v in crit.items()} for hat, crit in totals.items()
    }
    return {
        "model": result.get("model"),
        "provider": result.get("provider"),
        "prompt_versions": dict(sorted(versions.items())),
        "passed": result.get("passed", 0),
        "failed": result.get("failed", 0),
        "spent": result.get("spent"),
        "currency": result.get("currency"),
        "scores": means,
    }


def format_summary(name: str, s: dict[str, Any]) -> str:
    lines = [
        f"{name}: {s['provider']}/{s['model']}  passed {s['passed']}  failed {s['failed']}",
        "  prompts: " + ", ".join(f"{k} v{v}" for k, v in s["prompt_versions"].items()),
    ]
    if s["spent"] is not None and s["currency"]:
        lines.append(f"  spent: {s['currency']} {s['spent']}")
    if not s["scores"]:
        lines.append("  (no judge scores in this file)")
    for hat, crit in sorted(s["scores"].items()):
        lines.append(f"  {hat:7} " + "  ".join(f"{c}={crit.get(c, '-')}" for c in CRITERIA))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    for arg in argv:
        data = json.loads(Path(arg).read_text(encoding="utf-8"))
        print(format_summary(Path(arg).name, summarise(data)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
