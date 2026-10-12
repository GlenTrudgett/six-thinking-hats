from __future__ import annotations

import asyncio
import sys
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from six_hats import __version__
from six_hats.config.settings import Settings, load_settings
from six_hats.graph.resilience import AllHatsFailedError, Limits
from six_hats.graph.runner import new_run_id, run_workflow
from six_hats.hats.base import load_prompt
from six_hats.hats.registry import HATS, PROMPTS_BY_HAT
from six_hats.interfaces import diagnose as diag
from six_hats.llm.factory import ConfigError, create_model
from six_hats.llm.structured import StructuredOutputError
from six_hats.observability.logging import configure_logging
from six_hats.reporting.render import render_json, render_markdown
from six_hats.security.input_validation import InputError

app = typer.Typer(no_args_is_help=True, help="Six Thinking Hats")

EXIT_OK, EXIT_INTERNAL, EXIT_INPUT, EXIT_CONFIG, EXIT_DEGRADED, EXIT_NO_OUTPUT = 0, 1, 2, 3, 4, 5
_MAX_FILE_BYTES = 1_000_000


class OutputFormat(StrEnum):
    markdown = "markdown"
    json = "json"


def _fail(message: str, code: int) -> typer.Exit:
    typer.echo(message, err=True)
    return typer.Exit(code)


def _load_settings_or_exit() -> Settings:
    try:
        return load_settings()
    except ValidationError as exc:
        # Show where and why, never the offending value (it could be a secret).
        for err in exc.errors():
            where = ".".join(str(p) for p in err["loc"])
            typer.echo(f"config error: {where}: {err['msg']}", err=True)
        raise typer.Exit(EXIT_CONFIG) from exc


def _read_question(question: str | None, file: Path | None) -> str:
    if file is not None:
        if question is not None:
            raise InputError("give either QUESTION or --file, not both")
        if not file.is_file() or file.stat().st_size > _MAX_FILE_BYTES:
            raise InputError("question file must be an existing file under 1 MB")
        return file.read_text(encoding="utf-8", errors="strict")
    if question == "-":
        return sys.stdin.read(_MAX_FILE_BYTES + 1)
    if question is None:
        raise InputError("provide QUESTION, '-' for standard input, or --file")
    return question


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(__version__)


@app.command()
def hats() -> None:
    """List the hats, their roles and prompt versions."""
    for name, role in HATS.items():
        versions = ", ".join(f"{p} v{load_prompt(p).version}" for p in PROMPTS_BY_HAT[name])
        typer.echo(f"{name:7} {role}  [{versions}]")


@app.command()
def diagnose(
    ping: Annotated[
        bool, typer.Option("--ping", help="Make one small call to the model to prove it works.")
    ] = False,
) -> None:
    """Show versions and settings (secrets hidden) and optionally test the model connection."""
    settings = _load_settings_or_exit()
    for name, value in diag.collect(settings):
        typer.echo(f"{name:26} {value}")
    issues = diag.problems(settings)
    for issue in issues:
        typer.echo(f"PROBLEM: {issue}", err=True)
    if issues:
        raise typer.Exit(EXIT_CONFIG)
    if ping:
        ok, detail = asyncio.run(diag.ping(create_model(settings.llm)))
        typer.echo(f"{'model ping':26} {detail}")
        if not ok:
            raise typer.Exit(EXIT_NO_OUTPUT)


@app.command()
def run(
    question: Annotated[
        str | None, typer.Argument(help="The question or idea, or '-' to read standard input.")
    ] = None,
    file: Annotated[
        Path | None, typer.Option("--file", "-f", help="Read the question from a file.")
    ] = None,
    output_format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.markdown,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write the report to a file.")
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Overwrite the output file.")] = False,
) -> None:
    """Run the six-hats workflow on a question and print the report."""
    run_id = new_run_id()
    settings = _load_settings_or_exit()
    configure_logging(settings.log_level, settings.log_json)
    typer.echo(f"run: {run_id}", err=True)
    try:
        text = _read_question(question, file)
        if output is not None and output.exists() and not force:
            raise InputError(f"{output} exists; use --force to overwrite")
        model = create_model(settings.llm)
        report = asyncio.run(
            run_workflow(
                text,
                lambda _node: model,
                run_id=run_id,
                max_question_chars=settings.run.max_input_chars,
                limits=Limits(
                    node_timeout_seconds=settings.run.node_timeout_seconds,
                    node_retries=settings.run.node_retries,
                    retry_backoff_seconds=settings.run.retry_backoff_seconds,
                    max_context_chars=settings.run.max_context_chars,
                ),
            )
        )
    except InputError as exc:
        raise _fail(f"input error: {exc}", EXIT_INPUT) from exc
    except UnicodeDecodeError as exc:
        raise _fail("input error: question is not valid UTF-8", EXIT_INPUT) from exc
    except ConfigError as exc:
        raise _fail(f"config error: {exc}", EXIT_CONFIG) from exc
    except AllHatsFailedError as exc:
        raise _fail(f"error: {exc}. Check the model and your connection.", EXIT_NO_OUTPUT) from exc
    except StructuredOutputError as exc:
        raise _fail(
            f"error (run {run_id}): a model returned invalid output: {exc}", EXIT_INTERNAL
        ) from exc
    except Exception as exc:
        raise _fail(f"error (run {run_id}): {type(exc).__name__}", EXIT_INTERNAL) from exc

    rendered = (
        render_json(report) if output_format is OutputFormat.json else render_markdown(report)
    )
    if output is not None:
        output.write_text(rendered, encoding="utf-8")
        typer.echo(f"report written to {output}", err=True)
    else:
        typer.echo(rendered, nl=False)
    if report.degraded:
        raise typer.Exit(EXIT_DEGRADED)
