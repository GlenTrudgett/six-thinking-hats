"""Snapshots of the JSON schemas that cross a boundary (model output and the report).

A change to any of them must be deliberate. If you meant it, regenerate the snapshot and commit it:
    UPDATE_GOLDEN=1 uv run pytest tests/unit/test_golden_schema.py --no-cov
"""

import json
import os
from pathlib import Path

import pytest

from six_hats.schemas.framing import Framing
from six_hats.schemas.hat_output import HatOutput
from six_hats.schemas.presets import SequenceOverride
from six_hats.schemas.report import BlueCloseOutput, FinalReport

GOLDEN = Path(__file__).parent.parent / "golden" / "schemas.json"
MODELS = {
    "Framing": Framing,
    "HatOutput": HatOutput,
    "BlueCloseOutput": BlueCloseOutput,
    "FinalReport": FinalReport,
    "SequenceOverride": SequenceOverride,
}


def _current() -> dict[str, object]:
    return {name: model.model_json_schema() for name, model in MODELS.items()}


def test_schemas_match_the_golden_snapshot():
    current = _current()
    if os.environ.get("UPDATE_GOLDEN") == "1":
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        pytest.skip("golden snapshot rewritten")
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    changed = sorted(n for n in MODELS if current[n] != expected.get(n))
    assert not changed, (
        f"schema changed: {', '.join(changed)}. If intended, regenerate with UPDATE_GOLDEN=1 "
        "(see this file's docstring) and mention it in the changelog."
    )
