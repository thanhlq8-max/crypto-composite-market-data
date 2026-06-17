from __future__ import annotations

from crypto_composite.cli import parse_csv


def test_parse_csv_strips_empty_values() -> None:
    assert parse_csv("binance, okx,,bybit") == ["binance", "okx", "bybit"]
