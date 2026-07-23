"""One malformed record must not discard a venue's whole market_type block.

Regression tests for BUG_MEMORY B4: a record with a non-positive price, a
missing field, or a failed cast is skipped individually; sibling records in
the same payload still parse.
"""

from __future__ import annotations

import pytest

from crypto_composite.connectors.base import parse_records
from crypto_composite.connectors.binance import BinanceConnector
from crypto_composite.connectors.bybit import BybitConnector
from crypto_composite.connectors.coinbase import CoinbaseConnector
from crypto_composite.connectors.kraken import KrakenConnector
from crypto_composite.connectors.okx import OKXConnector


def test_parse_records_skips_failing_records_and_keeps_order() -> None:
    items = [1, "boom", 2, None, 3]

    def parse_one(item):
        return int(item) * 10

    assert parse_records(items, parse_one) == [10, 20, 30]
    assert parse_records(None, parse_one) == []


def test_binance_ohlcv_skips_bad_record_keeps_rest(monkeypatch) -> None:
    connector = BinanceConnector()
    payload = [
        [1000, "100", "110", "90", "105", "2", 0, "210", 12],
        [2000, "0", "0", "0", "0", "1", 0, "0", 1],       # non-positive prices
        [3000, "abc", "110", "90", "105", "2", 0, "210", 3],  # cast failure
        [4000, "101", "111", "91", "106", "2", 0, "212", 9],
    ]
    monkeypatch.setattr(connector, "_get", lambda url, params=None: payload)

    bars = connector.fetch_ohlcv("BTCUSDT", "spot_usdt", "15m", 4)

    assert [b.timestamp_ms for b in bars] == [1000, 4000]


def test_binance_trades_skips_bad_record_keeps_rest(monkeypatch) -> None:
    connector = BinanceConnector()
    payload = [
        {"T": 1010, "p": "105", "q": "0.5", "m": False, "a": 1},
        {"T": 1020, "p": "0", "q": "0.5", "m": False, "a": 2},    # zero price
        {"T": 1030, "q": "0.5", "m": False, "a": 3},              # missing field
        {"T": 1040, "p": "106", "q": "0.4", "m": True, "a": 4},
    ]
    monkeypatch.setattr(connector, "_get", lambda url, params=None: payload)

    trades = connector.fetch_recent_trades("BTCUSDT", "spot_usdt", 4)

    assert [t.timestamp_ms for t in trades] == [1010, 1040]


def test_okx_ohlcv_and_trades_skip_bad_records(monkeypatch) -> None:
    connector = OKXConnector()

    def fake_get(url: str, params: dict | None = None):
        if "candles" in url:
            return {"data": [
                ["3000", "101", "111", "91", "106", "2", "0", "212"],
                ["2000", "-5", "110", "90", "105", "2", "0", "210"],  # negative price
                ["1000", "100", "110", "90", "105", "2", "0", "210"],
            ]}
        if "trades" in url:
            return {"data": [
                {"ts": "1010", "px": "105", "sz": "0.5", "side": "buy", "tradeId": "a"},
                {"ts": "1020", "px": "105", "sz": "0", "side": "buy", "tradeId": "b"},  # zero size
                {"ts": "bad", "px": "105", "sz": "0.5", "side": "buy", "tradeId": "c"},  # cast failure
                {"ts": "1040", "px": "106", "sz": "0.4", "side": "sell", "tradeId": "d"},
            ]}
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)

    bars = connector.fetch_ohlcv("BTC-USDT", "spot_usdt", "15m", 3)
    trades = connector.fetch_recent_trades("BTC-USDT", "spot_usdt", 4)

    assert [b.timestamp_ms for b in bars] == [1000, 3000]
    assert [t.trade_id for t in trades] == ["a", "d"]


def test_bybit_ohlcv_and_trades_skip_bad_records(monkeypatch) -> None:
    connector = BybitConnector()

    def fake_get(url: str, params: dict | None = None):
        if "kline" in url:
            return {"result": {"list": [
                ["3000", "101", "111", "91", "106", "2", "212"],
                ["2000", "100", "110", "90", "0", "2", "210"],  # zero close
                ["1000", "100", "110", "90", "105", "2", "210"],
            ]}}
        if "recent-trade" in url:
            return {"result": {"list": [
                {"time": "1010", "price": "105", "size": "0.5", "side": "Buy", "execId": "a"},
                {"time": "1020", "price": "oops", "size": "0.5", "side": "Buy", "execId": "b"},  # cast failure
                {"time": "1030", "price": "106", "size": "0.4", "side": "Sell", "execId": "c"},
            ]}}
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)

    bars = connector.fetch_ohlcv("BTCUSDT", "spot_usdt", "15m", 3)
    trades = connector.fetch_recent_trades("BTCUSDT", "spot_usdt", 3)

    assert [b.timestamp_ms for b in bars] == [1000, 3000]
    assert [t.trade_id for t in trades] == ["a", "c"]


def test_coinbase_ohlcv_and_trades_skip_bad_records(monkeypatch) -> None:
    connector = CoinbaseConnector()

    def fake_get(url: str, params: dict | None = None):
        if "candles" in url:
            return [
                [1700000900, "91", "111", "101", "106", "2"],
                ["not-a-ts", "90", "110", "100", "105", "2"],  # sort key would crash pre-fix
                [1700000000, "90", "110", "100", "0", "2"],    # zero close
                [1700000300, "90", "110", "100", "105", "2"],
            ]
        if "trades" in url:
            return [
                {"time": "2023-11-14T22:13:20.000Z", "trade_id": 1, "price": "105", "size": "0.5", "side": "sell"},
                {"time": "2023-11-14T22:13:21.000Z", "trade_id": 2, "size": "0.5", "side": "sell"},  # missing price
                {"time": "2023-11-14T22:13:22.000Z", "trade_id": 3, "price": "106", "size": "0.4", "side": "buy"},
            ]
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)

    bars = connector.fetch_ohlcv("BTC-USDT", "spot_usdt", "15m", 4)
    trades = connector.fetch_recent_trades("BTC-USDT", "spot_usdt", 3)

    assert [b.timestamp_ms for b in bars] == [1700000300000, 1700000900000]
    assert [t.trade_id for t in trades] == ["1", "3"]


def test_coinbase_ohlcv_non_numeric_timestamp_record_is_skipped_not_now(monkeypatch) -> None:
    # _time_ms falls back to now_ms for bad string timestamps; the price guard
    # is what must reject the record, so pin every other field valid.
    connector = CoinbaseConnector()
    payload = [
        [1700000000, "90", "110", "100", "105", "2"],
        [1700000300, "90", "110", "100", "abc", "2"],  # cast failure in close
    ]
    monkeypatch.setattr(connector, "_get", lambda url, params=None: payload)

    bars = connector.fetch_ohlcv("BTC-USDT", "spot_usdt", "15m", 2)

    assert [b.timestamp_ms for b in bars] == [1700000000000]


def test_kraken_ohlcv_and_trades_skip_bad_records(monkeypatch) -> None:
    connector = KrakenConnector()

    def fake_get(url: str, params: dict | None = None):
        if "OHLC" in url:
            return {"error": [], "result": {"XBTUSDT": [
                [1700000000, "100", "110", "90", "105", "104", "2", 12],
                [1700000300, "100", "110", "90", "105", "104", "-1", 5],  # negative volume
                [1700000600, "101", "111", "91", "106", "105", "2", 9],
            ], "last": 1700000600}}
        if "Trades" in url:
            return {"error": [], "result": {"XBTUSDT": [
                ["105", "0.5", 1700000001.25, "b", "m", "", 1],
                ["-105", "0.5", 1700000002.25, "s", "m", "", 2],  # negative price
                ["106", "0.4", 1700000003.25, "s", "m", "", 3],
            ], "last": "170"}}
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)

    bars = connector.fetch_ohlcv("XBTUSDT", "spot_usdt", "15m", 3)
    trades = connector.fetch_recent_trades("XBTUSDT", "spot_usdt", 3)

    assert [b.timestamp_ms for b in bars] == [1700000000000, 1700000600000]
    assert [t.trade_id for t in trades] == ["1", "3"]


# --- Order book paths (BUG_MEMORY B6) ----------------------------------------
# The shared parse_book_levels helper already skips malformed list-shaped levels,
# but only candles/trades had regression coverage. These lock the same invariant
# in for every venue's order book, so a future connector change (or a new venue,
# as happened with the dict-shaped Gate futures book in B6) cannot silently
# reintroduce a whole-block loss on one bad public level. A bid whose price fails
# to cast ("boom") must be dropped, and the surrounding good levels must survive.

_BAD_LEVEL_BOOKS = {
    "binance": {"bids": [["104", "1.0"], ["boom", "2.0"], ["103", "0.5"]], "asks": [["106", "1.5"]]},
    "okx": {"data": [{"ts": "1020", "bids": [["104", "1.0"], ["boom", "2.0"], ["103", "0.5"]], "asks": [["106", "1.5"]]}]},
    "bybit": {"result": {"ts": 1020, "b": [["104", "1.0"], ["boom", "2.0"], ["103", "0.5"]], "a": [["106", "1.5"]]}},
    "coinbase": {"bids": [["104", "1.0", 2], ["boom", "2.0", 1], ["103", "0.5", 1]], "asks": [["106", "1.5", 1]], "time": "2023-11-14T22:13:21.000Z"},
    "kraken": {"error": [], "result": {"XBTUSDT": {"bids": [["104", "1.0", 1700000001], ["boom", "2.0", 1700000001], ["103", "0.5", 1700000001]], "asks": [["106", "1.5", 1700000002]]}}},
}


@pytest.mark.parametrize(
    "connector,symbol,payload",
    [
        (BinanceConnector(), "BTCUSDT", _BAD_LEVEL_BOOKS["binance"]),
        (OKXConnector(), "BTC-USDT", _BAD_LEVEL_BOOKS["okx"]),
        (BybitConnector(), "BTCUSDT", _BAD_LEVEL_BOOKS["bybit"]),
        (CoinbaseConnector(), "BTC-USDT", _BAD_LEVEL_BOOKS["coinbase"]),
        (KrakenConnector(), "XBTUSDT", _BAD_LEVEL_BOOKS["kraken"]),
    ],
)
def test_orderbook_skips_bad_level_keeps_rest(monkeypatch, connector, symbol, payload) -> None:
    monkeypatch.setattr(connector, "_get", lambda url, params=None: payload)

    book = connector.fetch_orderbook(symbol, "spot_usdt", 10)

    assert [price for price, _ in book.bids] == [104.0, 103.0]
    assert book.best_bid == 104.0 and book.best_ask == 106.0
