"""4h/1d timeframe tokens map to the correct venue-specific interval values."""

from __future__ import annotations

import pytest

from crypto_composite.connectors.base import UnsupportedTimeframeError
from crypto_composite.connectors.binance import BinanceConnector
from crypto_composite.connectors.bybit import BybitConnector
from crypto_composite.connectors.coinbase import CoinbaseConnector
from crypto_composite.connectors.kraken import KrakenConnector
from crypto_composite.connectors.okx import OKXConnector
from crypto_composite.engines.composite_ohlcv import _timeframe_ms


@pytest.mark.parametrize(
    "connector,symbol,param_key,expected_4h,expected_1d,empty_payload",
    [
        (BinanceConnector(), "BTCUSDT", "interval", "4h", "1d", []),
        (OKXConnector(), "BTC-USDT", "bar", "4H", "1Dutc", {"data": []}),
        (BybitConnector(), "BTCUSDT", "interval", "240", "D", {"result": {"list": []}}),
        (KrakenConnector(), "XBTUSDT", "interval", "240", "1440",
         {"error": [], "result": {"XBTUSDT": [], "last": 0}}),
    ],
)
def test_connectors_send_expected_interval_tokens(
    monkeypatch, connector, symbol, param_key, expected_4h, expected_1d, empty_payload
) -> None:
    sent: dict = {}

    def fake_get(url: str, params: dict | None = None):
        sent.update(params or {})
        return empty_payload

    monkeypatch.setattr(connector, "_get", fake_get)

    connector.fetch_ohlcv(symbol, "spot_usdt", "4h", 1)
    assert sent[param_key] == expected_4h
    connector.fetch_ohlcv(symbol, "spot_usdt", "1d", 1)
    assert sent[param_key] == expected_1d


def test_coinbase_sends_expected_granularity(monkeypatch) -> None:
    connector = CoinbaseConnector()
    sent: dict = {}

    def fake_get(url: str, params: dict | None = None):
        sent.update(params or {})
        return []

    monkeypatch.setattr(connector, "_get", fake_get)

    connector.fetch_ohlcv("BTC-USDT", "spot_usdt", "1d", 1)
    assert sent["granularity"] == "86400"


def test_coinbase_has_no_native_4h_granularity() -> None:
    # Live-verified 2026-07-12: /products/{id}/candles?granularity=14400
    # returns 400; the venue must opt out instead of shipping a broken call.
    with pytest.raises(UnsupportedTimeframeError, match="TIMEFRAME_UNSUPPORTED"):
        CoinbaseConnector().fetch_ohlcv("BTC-USDT", "spot_usdt", "4h", 1)


def test_unsupported_timeframe_still_raises() -> None:
    with pytest.raises(UnsupportedTimeframeError, match="TIMEFRAME_UNSUPPORTED"):
        BinanceConnector().fetch_ohlcv("BTCUSDT", "spot_usdt", "2h", 1)


def test_timeframe_ms_covers_new_tokens() -> None:
    assert _timeframe_ms("4h") == 4 * 3_600_000
    assert _timeframe_ms("1d") == 86_400_000
