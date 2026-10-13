"""Money is always shown with its currency code, never as a bare number."""

from __future__ import annotations

_SYMBOLS = {
    "USD": "$", "AUD": "$", "CAD": "$", "NZD": "$", "SGD": "$", "HKD": "$",
    "EUR": "€", "GBP": "£",
}  # fmt: skip


def format_money(amount: float, currency: str) -> str:
    """'USD $0.0123', 'AUD $0.0123', 'EUR €0.0123'; unknown codes show 'CHF 0.0123'."""
    symbol = _SYMBOLS.get(currency)
    return f"{currency} {symbol}{amount:.4f}" if symbol else f"{currency} {amount:.4f}"
