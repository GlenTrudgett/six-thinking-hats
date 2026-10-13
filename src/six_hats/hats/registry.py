from __future__ import annotations

from six_hats.hats.base import PromptName
from six_hats.schemas.hat_output import HatName

HATS: dict[HatName, str] = {
    "white": "Neutral and objective: facts and figures.",
    "red": "Emotional: feelings, intuition, hunches.",
    "black": "Cautious: risks and weaknesses.",
    "yellow": "Optimistic: benefits and hope.",
    "green": "Creative: new ideas and alternatives.",
    "blue": "Process control: frames the session, may pause between hats, writes the final report.",
}

PROMPTS_BY_HAT: dict[HatName, tuple[PromptName, ...]] = {
    "white": ("white",),
    "red": ("red",),
    "black": ("black",),
    "yellow": ("yellow",),
    "green": ("green",),
    "blue": ("blue_open", "blue_checkpoint", "blue_close"),
}
