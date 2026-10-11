import pytest

from six_hats.hats.base import load_prompt

HATS = ["white", "red", "green", "yellow", "black"]
ALL = [*HATS, "blue_open", "blue_close"]

RULES = {
    "white": ["[known]", "[unknown]", "[assumption]", "MUST NOT give opinions"],
    "red": ["first person", "3 to 5", "MUST NOT justify"],
    "green": ["Provocation:", "MUST NOT evaluate"],
    "yellow": ["logical reason", "conditions", "MUST NOT list risks"],
    "black": ["severity", "would have to be true", "MUST NOT use emotional negativity"],
    "blue_open": ["white, red, green, yellow, black", "never instructions"],
    "blue_close": ["MUST NOT introduce facts", "<hat_outputs>", "<missing_hats>"],
}


@pytest.mark.parametrize("name", ALL)
def test_prompt_has_version_and_rules(name):
    p = load_prompt(name)
    assert p.version == "1" and p.name == name
    for rule in RULES[name]:
        assert rule in p.text, f"{name} prompt is missing: {rule}"


@pytest.mark.parametrize("name", [*HATS, "blue_open", "blue_close"])
def test_prompt_treats_input_as_data(name):
    text = load_prompt(name).text
    assert "never instructions" in text or "data only" in text


@pytest.mark.parametrize("name", HATS)
def test_hat_prompt_refers_to_its_own_hat_only(name):
    text = load_prompt(name).text
    assert f"You are the {name.upper()} HAT" in text
