from __future__ import annotations

import pytest

from crypto_composite.symbol_map import SymbolMappingError, resolve_symbol


def test_resolve_symbol_for_supported_venues() -> None:
    assert resolve_symbol("BTC-USDT", "binance", "spot_usdt") == "BTCUSDT"
    assert resolve_symbol("BTC-USDT", "okx", "spot_usdt") == "BTC-USDT"
    assert resolve_symbol("BTC-USDT", "okx", "perp_usdt") == "BTC-USDT-SWAP"


def test_resolve_symbol_rejects_unsupported_quote() -> None:
    with pytest.raises(SymbolMappingError):
        resolve_symbol("BTC-USD", "binance", "spot_usdt")
