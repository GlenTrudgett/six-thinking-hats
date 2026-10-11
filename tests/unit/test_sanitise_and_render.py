import json

from six_hats.reporting.render import render_json, render_markdown
from six_hats.schemas.report import FinalReport, HatSummary
from six_hats.security.sanitise import sanitise_text


def test_strips_terminal_escapes_and_controls():
    assert sanitise_text("a\x1b[31mred\x1b[0m\x07b\x00c") == "aredbc"
    assert sanitise_text("\x1b]0;evil title\x07ok") == "ok"


def test_neutralises_html_and_unsafe_links():
    out = sanitise_text("<script>alert(1)</script> [x](javascript:alert(1)) 1 < 2")
    assert "<script" not in out and "(javascript:" not in out and "1 < 2" in out


def _report(**kw):
    base = dict(
        run_id="abc123",
        framing_summary="Framing \x1b[31mred",
        conclusions=["Do <img src=x onerror=1>"],
        hat_summaries=[HatSummary(hat="black", summary="Risky")],
    )
    return FinalReport(**{**base, **kw})


def test_markdown_shows_run_id_and_is_sanitised():
    md = render_markdown(_report())
    assert "`abc123`" in md and "\x1b" not in md and "<img" not in md
    assert "**Black:** Risky" in md


def test_markdown_flags_degraded():
    md = render_markdown(_report(degraded=True, missing_perspectives=["red"]))
    assert "Degraded run" in md and "red" in md


def test_json_is_valid_and_sanitised():
    data = json.loads(render_json(_report()))
    assert data["run_id"] == "abc123" and "\x1b" not in data["framing_summary"]
    assert "<img" not in data["conclusions"][0]
