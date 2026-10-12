"""Facts for troubleshooting. Never prints a secret: keys show only as set or not set."""

from __future__ import annotations

import asyncio
import platform
import sys
import time
from importlib import metadata

from langchain_core.language_models.chat_models import BaseChatModel

from six_hats import __version__
from six_hats.config.settings import Settings
from six_hats.graph.resilience import failure_message
from six_hats.hats.base import load_prompt
from six_hats.hats.registry import PROMPTS_BY_HAT

_PACKAGES = (
    "langchain",
    "langgraph",
    "langchain-core",
    "langchain-anthropic",
    "langchain-openai",
    "pydantic",
)


def _version(pkg: str) -> str:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return "not installed"


def collect(settings: Settings) -> list[tuple[str, str]]:
    llm, run = settings.llm, settings.run
    rows: list[tuple[str, str]] = [
        ("six-hats", __version__),
        ("python", sys.version.split()[0]),
        ("platform", f"{platform.system()} {platform.machine()}"),
        *((pkg, _version(pkg)) for pkg in _PACKAGES),
        ("provider", llm.provider),
        ("model", llm.model),
    ]
    if llm.provider == "anthropic":
        key = "set" if llm.anthropic_api_key is not None else "NOT SET"
        rows.append(("anthropic api key", key))
    else:
        rows += [("local base url", llm.local.base_url), ("local api key", "set (hidden)")]
    rows += [
        ("temperature", str(llm.temperature)),
        ("client timeout / retries", f"{llm.timeout_seconds}s / {llm.max_retries}"),
        (
            "node timeout / retries",
            f"{run.node_timeout_seconds}s / {run.node_retries}",
        ),
        ("max input chars", str(run.max_input_chars)),
        ("max context chars", str(run.max_context_chars)),
        ("log level", settings.log_level),
    ]
    prompts = sorted({p for names in PROMPTS_BY_HAT.values() for p in names})
    rows.append(("prompts", ", ".join(f"{p} v{load_prompt(p).version}" for p in prompts)))
    return rows


def problems(settings: Settings) -> list[str]:
    """Settings that would stop a run, as short plain sentences."""
    found: list[str] = []
    if settings.llm.provider == "anthropic" and settings.llm.anthropic_api_key is None:
        found.append("SIXHATS_LLM__ANTHROPIC_API_KEY is not set")
    return found


def _causes(exc: BaseException) -> str:
    """Type names of the underlying errors (e.g. ConnectError, gaierror), never their messages."""
    names: list[str] = []
    current = exc.__cause__ or exc.__context__
    while current is not None and len(names) < 4:
        names.append(type(current).__name__)
        current = current.__cause__ or current.__context__
    return f" <- {' <- '.join(names)}" if names else ""


async def ping(model: BaseChatModel, timeout: float = 30.0) -> tuple[bool, str]:
    """One tiny call. Returns (ok, detail). The detail never contains reply or prompt text."""
    start = time.perf_counter()
    try:
        async with asyncio.timeout(timeout):
            await model.ainvoke("Reply with the single word: ok")
    except Exception as exc:
        detail = failure_message(exc)
        return False, f"{type(exc).__name__}{' ' + detail if detail else ''}{_causes(exc)}"
    return True, f"ok in {int((time.perf_counter() - start) * 1000)} ms"
