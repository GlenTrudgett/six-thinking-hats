"""Timeouts, bounded retries and failure records for graph nodes.

A failed hat must not sink the run: it becomes a FailureRecord and the report is marked degraded.
Configuration errors are the exception; they are never degraded because every node would fail the
same way. Failure messages carry only the error type and an HTTP status, never prompt or reply text.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from six_hats.llm.factory import ConfigError
from six_hats.observability.logging import get_logger
from six_hats.schemas.failures import FailureRecord
from six_hats.schemas.hat_output import ThinkingHatName

_log = get_logger()
_TRANSIENT_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


@dataclass(frozen=True)
class Limits:
    node_timeout_seconds: float = 120.0
    node_retries: int = 1
    retry_backoff_seconds: float = 1.0
    max_context_chars: int = 24_000


DEFAULT_LIMITS = Limits()


class AllHatsFailedError(RuntimeError):
    """No hat produced any output, so there is nothing to report on (CLI exit code 5)."""


def is_transient(exc: BaseException) -> bool:
    """Worth another attempt: a timeout, a dropped connection, a rate limit or a server error."""
    if isinstance(exc, TimeoutError):
        return True
    if getattr(exc, "status_code", None) in _TRANSIENT_STATUS:
        return True
    names = {cls.__name__ for cls in type(exc).__mro__}
    return any("Timeout" in n or "Connection" in n for n in names)


def failure_message(exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    return f"HTTP {status}" if isinstance(status, int) else ""


async def run_guarded[T](
    call: Callable[[], Awaitable[T]],
    *,
    limits: Limits,
    node: str,
    run_id: str,
    hat: ThinkingHatName | None = None,
) -> tuple[T | None, FailureRecord | None]:
    """Run `call` with a per-attempt timeout and bounded retries of transient errors."""
    attempts = 0
    while True:
        attempts += 1
        try:
            async with asyncio.timeout(limits.node_timeout_seconds):
                return await call(), None
        except ConfigError:
            raise
        except Exception as exc:
            if is_transient(exc) and attempts <= limits.node_retries:
                _log.warning(
                    "node.retrying",
                    node=node,
                    hat=hat,
                    run_id=run_id,
                    attempt=attempts,
                    error_type=type(exc).__name__,
                )
                await asyncio.sleep(limits.retry_backoff_seconds * 2 ** (attempts - 1))
                continue
            record = FailureRecord(
                node=node,
                hat=hat,
                error_type=type(exc).__name__,
                attempts=attempts,
                message=failure_message(exc),
            )
            _log.error(
                "node.failed",
                node=node,
                hat=hat,
                run_id=run_id,
                error_type=record.error_type,
                attempts=attempts,
            )
            return None, record
