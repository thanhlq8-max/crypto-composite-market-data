from __future__ import annotations

import pytest

from crypto_composite.connectors.base import ConnectorDataError, UnsupportedTimeframeError
from crypto_composite.connectors.binance import BinanceConnector
from crypto_composite.connectors.bybit import BybitConnector
from crypto_composite.connectors.coinbase import CoinbaseConnector
from crypto_composite.connectors.okx import OKXConnector
from crypto_composite.engines.scan import ScanInputError, scan
from crypto_composite.symbol_map import SymbolMappingError, resolve_symbol


@pytest.mark.parametrize(
    "connector,symbol",
    [
        (BinanceConnector(), "BTCUSDT"),
        (OKXConnector(), "BTC-USDT"),
        (BybitConnector(), "BTCUSDT"),
        (CoinbaseConnector(), "BTC-USDT"),
    ],
)
def test_connectors_raise_domain_error_for_unsupported_timeframe(connector, symbol) -> None:
    with pytest.raises(UnsupportedTimeframeError, match="TIMEFRAME_UNSUPPORTED"):
        connector.fetch_ohlcv(symbol, "spot_usdt", "2h", 10)


@pytest.mark.parametrize(
    "connector,symbol,payload",
    [
        (BinanceConnector(), "BTCUSDT", {"bids": [], "asks": []}),
        (OKXConnector(), "BTC-USDT", {"data": [{"bids": [], "asks": [], "ts": "1000"}]}),
        (BybitConnector(), "BTCUSDT", {"result": {"b": [], "a": [], "ts": 1000}}),
        (CoinbaseConnector(), "BTC-USDT", {"bids": [], "asks": [], "time": "2023-11-14T22:13:20.000Z"}),
    ],
)
def test_connectors_raise_domain_error_for_empty_orderbook(monkeypatch, connector, symbol, payload) -> None:
    monkeypatch.setattr(connector, "_get", lambda url, params=None: payload)

    with pytest.raises(ConnectorDataError, match="EMPTY_ORDERBOOK"):
        connector.fetch_orderbook(symbol, "spot_usdt", 10)


def test_binance_connector_parses_public_payloads(monkeypatch) -> None:
    connector = BinanceConnector()

    def fake_get(url: str, params: dict | None = None):
        if "klines" in url:
            return [[1000, "100", "110", "90", "105", "2", 0, "210", 12]]
        if "aggTrades" in url:
            return [{"T": 1010, "p": "105", "q": "0.5", "m": False, "a": 123}]
        if "depth" in url:
            return {"bids": [["104", "1.0"], ["103", "0"]], "asks": [["106", "1.5"], ["107", "-2"]]}
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)

    bars = connector.fetch_ohlcv("BTCUSDT", "spot_usdt", "15m", 1)
    trades = connector.fetch_recent_trades("BTCUSDT", "spot_usdt", 1)
    book = connector.fetch_orderbook("BTCUSDT", "spot_usdt", 10)

    assert bars[0].close == 105.0
    assert bars[0].volume_quote == 210.0
    assert trades[0].side == "buy"
    assert trades[0].size_quote == 52.5
    assert book.best_bid == 104.0
    assert book.best_ask == 106.0
    assert book.depth_levels == 1


def test_okx_connector_parses_public_payloads(monkeypatch) -> None:
    connector = OKXConnector()

    def fake_get(url: str, params: dict | None = None):
        if "candles" in url:
            return {"data": [["1000", "100", "110", "90", "105", "2", "0", "210"]]}
        if "trades" in url:
            return {"data": [{"ts": "1010", "px": "105", "sz": "0.5", "side": "buy", "tradeId": "abc"}]}
        if "books" in url:
            return {"data": [{"ts": "1020", "bids": [["104", "1.0"]], "asks": [["106", "1.5"]]}]}
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)

    bars = connector.fetch_ohlcv("BTC-USDT", "spot_usdt", "15m", 1)
    trades = connector.fetch_recent_trades("BTC-USDT", "spot_usdt", 1)
    book = connector.fetch_orderbook("BTC-USDT", "spot_usdt", 10)

    assert bars[0].timestamp_ms == 1000
    assert bars[0].volume_quote == 210.0
    assert trades[0].is_aggressive is True
    assert book.mid == 105.0
    assert book.spread == 2.0


def test_bybit_connector_parses_public_payloads(monkeypatch) -> None:
    connector = BybitConnector()

    def fake_get(url: str, params: dict | None = None):
        if "kline" in url:
            return {"result": {"list": [["1000", "100", "110", "90", "105", "2", "210"]]}}
        if "recent-trade" in url:
            return {"result": {"list": [{"time": "1010", "price": "105", "size": "0.5", "side": "Sell", "execId": "abc"}]}}
        if "orderbook" in url:
            return {"result": {"ts": 1020, "b": [["104", "1.0"]], "a": [["106", "1.5"]]}}
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)

    bars = connector.fetch_ohlcv("BTCUSDT", "spot_usdt", "15m", 1)
    trades = connector.fetch_recent_trades("BTCUSDT", "spot_usdt", 1)
    book = connector.fetch_orderbook("BTCUSDT", "spot_usdt", 10)

    assert bars[0].open == 100.0
    assert bars[0].volume_quote == 210.0
    assert trades[0].side == "sell"
    assert trades[0].is_aggressive is True
    assert book.mid == 105.0


def test_coinbase_connector_parses_public_payloads(monkeypatch) -> None:
    connector = CoinbaseConnector()

    def fake_get(url: str, params: dict | None = None):
        if "candles" in url:
            return [[1700000000, "90", "110", "100", "105", "2"]]
        if "trades" in url:
            return [
                {
                    "time": "2023-11-14T22:13:20.000Z",
                    "trade_id": 123,
                    "price": "105",
                    "size": "0.5",
                    "side": "sell",
                }
            ]
        if "book" in url:
            return {
                "bids": [["104", "1.0", 2]],
                "asks": [["106", "1.5", 1]],
                "time": "2023-11-14T22:13:21.000Z",
            }
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)

    bars = connector.fetch_ohlcv("BTC-USDT", "spot_usdt", "15m", 1)
    trades = connector.fetch_recent_trades("BTC-USDT", "spot_usdt", 1)
    book = connector.fetch_orderbook("BTC-USDT", "spot_usdt", 10)

    assert bars[0].timestamp_ms == 1700000000000
    assert bars[0].volume_quote == 210.0
    assert trades[0].side == "buy"
    assert trades[0].is_aggressive is True
    assert book.best_bid == 104.0
    assert book.best_ask == 106.0
    assert book.mid == 105.0


def test_coinbase_symbol_mapping_is_spot_only() -> None:
    assert resolve_symbol("BTC-USDT", "coinbase", "spot_usdt") == "BTC-USDT"
    with pytest.raises(SymbolMappingError, match="Coinbase connector supports spot_usdt only"):
        resolve_symbol("BTC-USDT", "coinbase", "perp_usdt")


def test_scan_rejects_unsupported_venue_before_connector_lookup() -> None:
    with pytest.raises(ScanInputError, match="VENUE_UNSUPPORTED"):
        scan("BTC-USDT", ["binance", "unknownvenue"], ["spot_usdt"], "15m", 10, depth=5)
