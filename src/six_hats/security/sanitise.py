"""Neutralise model-derived text before it is shown in a terminal or written as Markdown."""

from __future__ import annotations

import re

_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)?|[@-Z\\-_])")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_HTML_TAG = re.compile(r"<(?=[A-Za-z/!?])")
_UNSAFE_LINK = re.compile(r"\]\(\s*(?:javascript|data|vbscript):", re.IGNORECASE)


def sanitise_text(text: str) -> str:
    text = _ANSI.sub("", text)
    text = _CONTROL.sub("", text)
    text = _HTML_TAG.sub("&lt;", text)
    return _UNSAFE_LINK.sub("](#blocked:", text)
