from __future__ import annotations

import pytest

from crypto_composite.symbol_map import SymbolMappingError, resolve_symbol


def test_resolve_symbol_normalizes_case() -> None:
    assert resolve_symbol("eth-usdt", "BINANCE", "SPOT_USDT") == "ETHUSDT"


def test_resolve_symbol_for_bybit_perp_uses_linear_symbol() -> None:
    assert resolve_symbol("BTC-USDT", "bybit", "perp_usdt") == "BTCUSDT"


def test_resolve_symbol_rejects_unsupported_venue() -> None:
    with pytest.raises(SymbolMappingError, match="VENUE_UNSUPPORTED"):
        resolve_symbol("BTC-USDT", "unknownvenue", "spot_usdt")


def test_resolve_symbol_rejects_unsupported_market_type() -> None:
    with pytest.raises(SymbolMappingError, match="MARKET_TYPE_UNSUPPORTED"):
        resolve_symbol("BTC-USDT", "binance", "inverse_usd")


def test_resolve_symbol_rejects_malformed_asset() -> None:
    with pytest.raises(SymbolMappingError, match="ASSET_FORMAT_UNSUPPORTED"):
        resolve_symbol("BTCUSDT", "binance", "spot_usdt")
