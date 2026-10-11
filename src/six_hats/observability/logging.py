"""structlog setup with redaction. Logs go to stderr."""

from __future__ import annotations

import logging
import sys

import structlog

from six_hats.security.redaction import redact_processor


class _StderrLoggerFactory:
    """Resolve sys.stderr at call time, so a replaced or closed stream never breaks logging."""

    def __call__(self, *_args: object) -> structlog.PrintLogger:
        return structlog.PrintLogger(file=sys.stderr)


def configure_logging(level: str = "INFO", json: bool = False) -> None:
    renderer = structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_processor,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        logger_factory=_StderrLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str = "six_hats") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
