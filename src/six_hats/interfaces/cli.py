from __future__ import annotations

import asyncio

import typer

from six_hats import __version__
from six_hats.config.settings import load_settings
from six_hats.hats.base import run_hat
from six_hats.hats.registry import HATS, IMPLEMENTED
from six_hats.llm.factory import ConfigError, create_model
from six_hats.observability.logging import configure_logging
from six_hats.security.input_validation import InputError, validate_request

app = typer.Typer(no_args_is_help=True, help="Six Thinking Hats")


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(__version__)


@app.command()
def hats() -> None:
    """List the hats."""
    for name, desc in HATS.items():
        status = "ready" if name in IMPLEMENTED else "planned"
        typer.echo(f"{name:7} [{status}] {desc}")


@app.command()
def run(request: str, hat: str = "white") -> None:
    """Run a single hat (Phase 1)."""
    settings = load_settings()
    configure_logging(settings.log_level, settings.log_json)
    try:
        text = validate_request(request, settings.run.max_input_chars)
    except InputError as exc:
        typer.echo(f"input error: {exc}", err=True)
        raise typer.Exit(2) from exc
    if hat not in IMPLEMENTED:
        typer.echo(f"hat '{hat}' is not implemented yet", err=True)
        raise typer.Exit(2)
    try:
        model = create_model(settings.llm)
    except ConfigError as exc:
        typer.echo(f"config error: {exc}", err=True)
        raise typer.Exit(3) from exc
    out = asyncio.run(run_hat("white", model, text))
    typer.echo(out.model_dump_json(indent=2))
