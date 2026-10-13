"""Progress events and cost estimates."""

import pytest
from typer.testing import CliRunner

from six_hats.graph.runner import estimate_cost, run_workflow
from six_hats.interfaces import cli
from six_hats.reporting.render import render_markdown
from tests.support.hats_fake import make_hats_fake

Q = "Should we adopt a four-day work week?"


async def test_progress_events_cover_the_run_in_order():
    events: list[tuple[str, str]] = []
    model = make_hats_fake()
    report = await run_workflow(
        Q, lambda _n: model, run_id="pc1", on_progress=lambda n, m: events.append((n, m))
    )
    nodes = [n for n, _ in events]
    assert nodes[0] == "intake" and nodes[-1] == "blue_close"
    assert nodes.index("blue_open") < nodes.index("white") < nodes.index("blue_close")
    assert set(nodes) >= {"white", "red", "green", "yellow", "black"}
    assert report.elapsed_seconds is not None and report.elapsed_seconds >= 0


def test_estimate_cost():
    totals = {"input_tokens": 1_000_000, "output_tokens": 500_000, "total_tokens": 1_500_000}
    assert estimate_cost(totals, 3.0, 15.0) == pytest.approx(10.5)
    assert estimate_cost(totals, None, 15.0) is None
    assert estimate_cost(totals, 3.0, None) is None


async def test_cost_only_when_prices_given_and_rendered():
    model = make_hats_fake()
    plain = await run_workflow(Q, lambda _n: model, run_id="pc2")
    assert plain.estimated_cost is None and "est. cost" not in render_markdown(plain)
    priced = await run_workflow(
        Q,
        lambda _n: make_hats_fake(),
        run_id="pc3",
        price_input_per_mtok=1,
        price_output_per_mtok=2,
        price_currency="AUD",
    )
    # fake models report no usage, so tokens and cost are zero but present
    assert priced.estimated_cost == 0 and priced.cost_currency == "AUD"
    assert "est. cost: AUD $0.0000" in render_markdown(priced)


runner = CliRunner()


def test_cli_progress_and_usage_on_stderr_and_quiet(monkeypatch):
    monkeypatch.setattr(cli, "create_model", lambda _cfg: make_hats_fake())
    monkeypatch.setenv("SIXHATS_LLM__ANTHROPIC_API_KEY", "sk-ant-test")
    r = CliRunner().invoke(cli.app, ["run", "q"])
    assert r.exit_code == 0 and "blue_open:" in r.output and "usage:" in r.output
    q = CliRunner().invoke(cli.app, ["run", "q", "--quiet"])
    assert "blue_open:" not in q.output and "usage:" in q.output


async def test_no_cost_without_a_currency():
    r = await run_workflow(
        Q,
        lambda _n: make_hats_fake(),
        run_id="pc4",
        price_input_per_mtok=1,
        price_output_per_mtok=2,
    )
    assert r.estimated_cost is None and r.cost_currency is None


def test_money_always_carries_the_currency():
    from six_hats.reporting.money import format_money

    assert format_money(0.5, "AUD") == "AUD $0.5000"
    assert format_money(0.5, "USD") == "USD $0.5000"
    assert format_money(0.5, "EUR") == "EUR €0.5000"
    assert format_money(0.5, "CHF") == "CHF 0.5000"


def test_price_settings_need_all_three_and_a_valid_currency():
    import pytest
    from pydantic import ValidationError

    from six_hats.config.settings import RunSettings

    ok = RunSettings(price_input_per_mtok=2, price_output_per_mtok=10, price_currency="aud")
    assert ok.price_currency == "AUD"
    assert RunSettings().price_currency is None
    for bad in (
        {"price_input_per_mtok": 2, "price_output_per_mtok": 10},
        {"price_input_per_mtok": 2, "price_currency": "USD"},
        {"price_currency": "USD"},
        {"price_input_per_mtok": 2, "price_output_per_mtok": 10, "price_currency": "$"},
    ):
        with pytest.raises(ValidationError):
            RunSettings(**bad)
