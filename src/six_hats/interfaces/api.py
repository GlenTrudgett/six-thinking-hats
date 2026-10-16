"""A small local web API for the frontend. Optional: install with the `web` extra.

It binds to loopback by default and keeps the model key on the server; the browser never sees it.
`POST /api/run` answers with a server-sent event stream: `progress` events, then one `report` event
(or one `error` event).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

from six_hats import __version__
from six_hats.config.settings import Settings
from six_hats.graph.resilience import AllHatsFailedError, Limits
from six_hats.graph.runner import new_run_id, run_workflow
from six_hats.llm.factory import ConfigError, create_model
from six_hats.llm.structured import StructuredOutputError
from six_hats.observability.logging import get_logger
from six_hats.schemas.hat_output import THINKING_HATS, SequenceStep, blue_step_problem
from six_hats.schemas.presets import PRESETS, SequenceOverride
from six_hats.security.input_validation import InputError

_log = get_logger()
MAX_QUESTION_CHARS = 8000


class RunRequest(BaseModel):
    question: Annotated[str, Field(min_length=1, max_length=MAX_QUESTION_CHARS)]
    mode: Literal["auto", "parallel"] = "auto"
    preset: str | None = None
    sequence: list[SequenceStep] | None = Field(default=None, min_length=1, max_length=8)

    @field_validator("sequence")
    @classmethod
    def _blue_rules(cls, value: list[SequenceStep] | None) -> list[SequenceStep] | None:
        if value is not None and (problem := blue_step_problem(value)):
            raise ValueError(problem)
        return value


def _override(req: RunRequest) -> SequenceOverride | None:
    chosen = [req.mode == "parallel", req.preset is not None, req.sequence is not None]
    if sum(chosen) > 1:
        raise InputError("choose only one of parallel mode, a preset or a sequence")
    if req.mode == "parallel":
        return SequenceOverride(parallel=True)
    if req.preset is not None:
        if req.preset not in PRESETS:
            raise InputError(f"unknown preset '{req.preset}'")
        return SequenceOverride.model_validate({"preset": req.preset})
    if req.sequence is not None:
        return SequenceOverride(sequence=req.sequence)
    return None


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def create_app(
    settings: Settings,
    *,
    allowed_origins: list[str] | None = None,
    keepalive_seconds: float = 10.0,
) -> FastAPI:
    app = FastAPI(title="Six Thinking Hats", version=__version__, docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/presets")
    async def presets() -> dict[str, object]:
        return {
            "hats": list(THINKING_HATS),
            "presets": [
                {
                    "id": p.id,
                    "title": p.title,
                    "use_when": p.use_when,
                    "sequence": list(p.sequence),
                    "source": p.source,
                }
                for p in PRESETS.values()
            ],
        }

    @app.post("/api/run")
    async def run(req: RunRequest) -> StreamingResponse:
        run_id = new_run_id()
        queue: asyncio.Queue[tuple[str, object] | None] = asyncio.Queue()

        async def work() -> None:
            try:
                override = _override(req)
                model = create_model(settings.llm)
                r = settings.run
                prices = settings.prices()
                report = await run_workflow(
                    req.question,
                    lambda _node: model,
                    run_id=run_id,
                    max_question_chars=r.max_input_chars,
                    limits=Limits(
                        node_timeout_seconds=r.node_timeout_seconds,
                        node_retries=r.node_retries,
                        retry_backoff_seconds=r.retry_backoff_seconds,
                        max_context_chars=r.max_context_chars,
                    ),
                    override=override,
                    on_progress=lambda node, msg: queue.put_nowait(
                        ("progress", {"node": node, "message": msg})
                    ),
                    price_input_per_mtok=prices[0],
                    price_output_per_mtok=prices[1],
                    price_currency=prices[2],
                )
                queue.put_nowait(("report", report.model_dump(mode="json")))
            except (InputError, ValidationError) as exc:
                queue.put_nowait(("error", {"kind": "input", "message": str(exc)[:300]}))
            except ConfigError:
                queue.put_nowait(
                    ("error", {"kind": "config", "message": "model configuration error"})
                )
            except AllHatsFailedError:
                queue.put_nowait(
                    ("error", {"kind": "no_output", "message": "no hat produced output"})
                )
            except StructuredOutputError:
                queue.put_nowait(
                    (
                        "error",
                        {"kind": "invalid_output", "message": "a model returned invalid output"},
                    )
                )
            except Exception as exc:
                _log.error("api.run_failed", run_id=run_id, error=type(exc).__name__)
                queue.put_nowait(
                    ("error", {"kind": "internal", "message": f"internal error (run {run_id})"})
                )
            finally:
                queue.put_nowait(None)

        async def stream() -> AsyncIterator[str]:
            task = asyncio.create_task(work())
            try:
                yield _sse("start", {"run_id": run_id})
                while True:
                    try:
                        item = await asyncio.wait_for(queue.get(), keepalive_seconds)
                    except TimeoutError:
                        # An SSE comment: ignored by the browser, but stops proxies and browsers
                        # from treating a long quiet step (a slow model) as a dead connection.
                        yield ": keepalive\n\n"
                        continue
                    if item is None:
                        break
                    yield _sse(*item)
            finally:
                task.cancel()  # the browser went away: stop spending tokens

        return StreamingResponse(stream(), media_type="text/event-stream")

    return app
