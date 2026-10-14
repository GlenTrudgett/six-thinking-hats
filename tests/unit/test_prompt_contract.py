"""Contract every prompt must meet. New prompt files are picked up automatically."""

import re
from importlib import resources

import pytest

from six_hats.hats.base import load_prompt
from six_hats.schemas.presets import PRESETS, describe_presets

NAMES = sorted(
    p.name.removesuffix(".md")
    for p in resources.files("six_hats.hats.prompts").iterdir()
    if p.name.endswith(".md")
)
LIMIT = re.compile(r"at most \d|\b\d+ to \d+\b|under \d+|\b\d+ (?:or fewer|items)")
DATA_RULE = ("never instructions", "data only", "is data", "are data")


def _colour(name: str) -> str:
    return name.split("_")[0].upper()


def test_every_expected_prompt_exists():
    assert {"white", "red", "green", "yellow", "black", "blue_open", "blue_close"} <= set(NAMES)


@pytest.mark.parametrize("name", NAMES)
def test_prompt_contract(name):
    prompt = load_prompt(name)
    text = prompt.text
    assert prompt.version.isdigit() and int(prompt.version) >= 1, "version must be a whole number"
    assert f"You are the {_colour(name)} HAT" in text, "must name its own hat"
    others = {"WHITE", "RED", "GREEN", "YELLOW", "BLACK", "BLUE"} - {_colour(name)}
    assert not any(f"You are the {o} HAT" in text for o in others), "must not claim another hat"
    assert LIMIT.search(text), "must state a length or count limit"
    assert any(rule in text for rule in DATA_RULE), "must say user text is data, not instructions"
    assert len(text) < 4000, "keep prompts short; long prompts drift and cost tokens"
    assert "\t" not in text and text == text.strip()


@pytest.mark.parametrize("name", NAMES)
def test_only_known_placeholders_remain(name):
    placeholders = set(re.findall(r"\{\{(\w+)\}\}", load_prompt(name).text))
    assert placeholders <= ({"presets"} if name == "blue_open" else set())


def test_blue_open_receives_every_preset():
    system = load_prompt("blue_open").text.replace("{{presets}}", describe_presets())
    assert "{{" not in system
    for preset_id, preset in PRESETS.items():
        assert preset_id in system
        assert ", ".join(preset.sequence) in system, f"order of {preset_id} not shown"


def test_blue_open_only_lists_the_coloured_hats():
    text = load_prompt("blue_open").text
    assert "using only: white, red, green, yellow, black" in text
