"""A hat is a versioned prompt plus a schema. User text is passed only inside data blocks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import resources
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from six_hats.llm.structured import ainvoke_structured
from six_hats.schemas.framing import Framing
from six_hats.schemas.hat_output import HatOutput, ThinkingHatName

PromptName = Literal["white", "red", "green", "yellow", "black", "blue_open", "blue_close"]
_FRONT_MATTER = re.compile(r"\A---\nversion:\s*(\S+)\n---\n", re.ASCII)


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    text: str


def load_prompt(name: PromptName) -> Prompt:
    raw = resources.files("six_hats.hats.prompts").joinpath(f"{name}.md").read_text("utf-8")
    match = _FRONT_MATTER.match(raw)
    if match is None:
        raise ValueError(f"prompt {name} has no version header")
    return Prompt(name=name, version=match.group(1), text=raw[match.end() :].strip())


def data_block(tag: str, content: str) -> str:
    """Wrap untrusted text in a delimited block. A closing tag inside it is neutralised."""
    safe = content.replace(f"</{tag}>", f"<\\/{tag}>")
    return f"<{tag}>\n{safe}\n</{tag}>"


def brief_block(framing: Framing) -> str:
    body = (
        f"focus: {framing.focus}\nobjective: {framing.objective}\n"
        f"thinking_type: {framing.thinking_type}"
    )
    return data_block("brief", body)


async def run_hat(
    hat: ThinkingHatName,
    model: BaseChatModel,
    question: str,
    framing: Framing,
    config: RunnableConfig | None = None,
) -> HatOutput:
    prompt = load_prompt(hat)
    user = f"{data_block('question', question)}\n\n{brief_block(framing)}"
    output = await ainvoke_structured(model, HatOutput, prompt.text, user, config=config)
    return output.model_copy(update={"hat": hat})
