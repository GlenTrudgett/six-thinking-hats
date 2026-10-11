"""A hat is a prompt plus a schema; behaviour lives in the prompt file."""

from __future__ import annotations

from importlib import resources

from langchain_core.language_models.chat_models import BaseChatModel

from six_hats.llm.structured import ainvoke_structured
from six_hats.schemas.hat_output import HatName, HatOutput


def load_prompt(hat: HatName) -> str:
    return resources.files("six_hats.hats.prompts").joinpath(f"{hat}.md").read_text("utf-8")


async def run_hat(hat: HatName, model: BaseChatModel, request: str) -> HatOutput:
    output = await ainvoke_structured(
        model, HatOutput, load_prompt(hat), f"<request>\n{request}\n</request>"
    )
    return output.model_copy(update={"hat": hat})
