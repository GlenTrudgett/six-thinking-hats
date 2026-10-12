"""Render a FinalReport as Markdown or JSON. All model-derived text is sanitised first."""

from __future__ import annotations

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
    if report.mode == "sequential" and report.sequence:
        parts.append(
            "Sequence: " + " → ".join(["Blue", *(h.capitalize() for h in report.sequence), "Blue"])
        )
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
