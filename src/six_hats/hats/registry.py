from __future__ import annotations

from six_hats.schemas.hat_output import HatName

HATS: dict[HatName, str] = {
    "white": "Neutral and objective: facts and figures.",
    "red": "Emotional: feelings, intuition, hunches.",
    "black": "Cautious: risks and weaknesses.",
    "yellow": "Optimistic: benefits and hope.",
    "green": "Creative: new ideas and alternatives.",
    "blue": "Process control: organises the thinking.",
}

IMPLEMENTED: frozenset[HatName] = frozenset({"white"})
