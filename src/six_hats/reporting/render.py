"""Render a FinalReport as Markdown or JSON. All model-derived text is sanitised first."""

from __future__ import annotations

from six_hats.reporting.money import format_money
from six_hats.schemas.presets import PRESETS
from six_hats.schemas.report import FinalReport
from six_hats.security.sanitise import sanitise_text


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {sanitise_text(i)}" for i in items) if items else "_None._"


def render_markdown(report: FinalReport) -> str:
    parts = [
        "# Six Thinking Hats report",
        f"Run: `{report.run_id}`  \nGenerated: {report.generated_at:%Y-%m-%d %H:%M} UTC",
    ]
    if report.degraded:
        missing = ", ".join(report.missing_perspectives) or "unknown"
        parts.append(f"> **Degraded run.** Missing perspectives: {missing}.")
        for f in report.failures:
            detail = f" ({f.message})" if f.message else ""
            parts.append(f"> - `{f.node}`{' / ' + f.hat if f.hat else ''}: {f.error_type}{detail}")
    if report.mode == "sequential" and report.sequence:
        line = "Sequence: " + " → ".join(
            ["Blue", *(h.capitalize() for h in report.sequence), "Blue"]
        )
        if report.preset:
            preset = PRESETS.get(report.preset)
            name = preset.title if preset else "Custom order"
            note = (
                " (advanced preset; secondary source, not the book)"
                if report.preset_source == "advanced"
                else ""
            )
            line = f"Preset: {name}{note}  \n{line}"
        parts.append(line)
    parts += [
        "## Framing",
        sanitise_text(report.framing_summary),
        "## Conclusions",
        _bullets(report.conclusions),
        "## Perspectives",
        "\n".join(
            f"- **{s.hat.capitalize()}:** {sanitise_text(s.summary)}" for s in report.hat_summaries
        )
        or "_None._",
        "## Agreements",
        _bullets(report.agreements),
        "## Tensions",
        _bullets(report.tensions),
        "## Recommended next steps",
        _bullets(report.recommended_next_steps),
        "## Open questions",
        _bullets(report.open_questions),
    ]
    footer = [f"models: {', '.join(report.models_used) or 'n/a'}"]
    if report.token_usage:
        footer.append(
            f"tokens: {report.token_usage.get('input_tokens', 0)} in / "
            f"{report.token_usage.get('output_tokens', 0)} out"
        )
    if report.elapsed_seconds is not None:
        footer.append(f"time: {report.elapsed_seconds}s")
    if report.estimated_cost is not None and report.cost_currency:
        footer.append(f"est. cost: {format_money(report.estimated_cost, report.cost_currency)}")
    parts.append("---\n" + " · ".join(footer))
    return "\n\n".join(parts) + "\n"


def render_json(report: FinalReport) -> str:
    safe = report.model_copy(
        update={
            "framing_summary": sanitise_text(report.framing_summary),
            "conclusions": [sanitise_text(x) for x in report.conclusions],
            "agreements": [sanitise_text(x) for x in report.agreements],
            "tensions": [sanitise_text(x) for x in report.tensions],
            "recommended_next_steps": [sanitise_text(x) for x in report.recommended_next_steps],
            "open_questions": [sanitise_text(x) for x in report.open_questions],
            "hat_summaries": [
                s.model_copy(update={"summary": sanitise_text(s.summary)})
                for s in report.hat_summaries
            ],
        }
    )
    return safe.model_dump_json(indent=2) + "\n"
