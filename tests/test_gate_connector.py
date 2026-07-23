"""Gate.io connector: spot base units, futures contract-scaled units, mappings."""

from __future__ import annotations

import pytest

from crypto_composite.connectors import gate as gate_module
from crypto_composite.connectors.base import UnsupportedTimeframeError
from crypto_composite.connectors.gate import GateConnector
from crypto_composite.symbol_map import (
    PERP_VENUES,
    SUPPORTED_VENUES,
    resolve_symbol,
    venue_supports_market_type,
)

MULT = 0.0001


@pytest.fixture(autouse=True)
def _clear_multiplier_cache():
    gate_module._MULTIPLIER_CACHE.clear()
    yield
    gate_module._MULTIPLIER_CACHE.clear()


def _gate(monkeypatch, routes):
    connector = GateConnector()

    def fake_get(url: str, params: dict | None = None):
        for token, payload in routes.items():
            if token in url:
                return payload
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)
    return connector


def test_gate_registered_as_perp_capable_venue() -> None:
    assert "gate" in SUPPORTED_VENUES
    assert "gate" in PERP_VENUES
    assert venue_supports_market_type("gate", "perp_usdt")
    assert venue_supports_market_type("gate", "spot_usdt")


def test_gate_symbol_mapping_uses_underscore() -> None:
    assert resolve_symbol("BTC-USDT", "gate", "spot_usdt") == "BTC_USDT"
    assert resolve_symbol("ETH-USDT", "gate", "perp_usdt") == "ETH_USDT"


def test_gate_spot_ohlcv_column_order_and_base_volume(monkeypatch) -> None:
    connector = _gate(monkeypatch, {
        # [ts_s, quote_vol, close, high, low, open, base_vol, closed]
        "spot/candlesticks": [["1783851300", "925580.73", "63880.5", "63936.8", "63870.0", "63927.9", "14.4845", "true"]],
    })

    bars = connector.fetch_ohlcv("BTC_USDT", "spot_usdt", "15m", 1)
    bar = bars[0]

    assert bar.timestamp_ms == 1783851300000
    assert bar.open == 63927.9 and bar.close == 63880.5
    assert bar.high == 63936.8 and bar.low == 63870.0
    assert bar.volume_base == pytest.approx(14.4845)
    assert bar.volume_quote == pytest.approx(925580.73)


def test_gate_spot_trade_and_book_use_base_units(monkeypatch) -> None:
    connector = _gate(monkeypatch, {
        "spot/trades": [{"create_time_ms": "1783852182004.2", "side": "sell", "amount": "0.000782", "price": "63886.6", "id": 9}],
        "spot/order_book": {"current": 1783852182004, "bids": [["63886", "0.5"]], "asks": [["63888", "0.4"]]},
    })

    trades = connector.fetch_recent_trades("BTC_USDT", "spot_usdt", 1)
    book = connector.fetch_orderbook("BTC_USDT", "spot_usdt", 5)

    assert trades[0].side == "sell"
    assert trades[0].size_base == pytest.approx(0.000782)
    assert trades[0].timestamp_ms == 1783852182004
    assert book.bids[0] == (63886.0, pytest.approx(0.5))
    assert book.best_bid == 63886.0 and book.best_ask == 63888.0


def test_gate_perp_scales_contracts_to_base(monkeypatch) -> None:
    connector = _gate(monkeypatch, {
        "contracts/BTC_USDT": {"quanto_multiplier": str(MULT), "type": "direct"},
        "futures/usdt/candlesticks": [{"t": 1783851300, "o": "63913.2", "h": "63913.3", "l": "63855.4", "c": "63855.4", "v": 1514198, "sum": "9673040.06"}],
        "futures/usdt/trades": [{"id": 790752929, "create_time_ms": 1783852195.359, "size": -2183, "price": "63850.1"}],
        "futures/usdt/order_book": {"current": 1783852195359, "bids": [{"s": 7490, "p": "63860.6"}], "asks": [{"s": 5000, "p": "63870.0"}]},
    })

    bars = connector.fetch_ohlcv("BTC_USDT", "perp_usdt", "15m", 1)
    trades = connector.fetch_recent_trades("BTC_USDT", "perp_usdt", 1)
    book = connector.fetch_orderbook("BTC_USDT", "perp_usdt", 5)

    # candle base volume = contracts * multiplier
    assert bars[0].volume_base == pytest.approx(1514198 * MULT)
    assert bars[0].volume_quote == pytest.approx(9673040.06)
    # negative signed size => taker sell; magnitude scaled to base
    assert trades[0].side == "sell"
    assert trades[0].size_base == pytest.approx(2183 * MULT)
    assert book.bids[0] == (63860.6, pytest.approx(7490 * MULT))


def test_gate_perp_orderbook_skips_malformed_levels(monkeypatch) -> None:
    # BUG_MEMORY B4 invariant for the dict-shaped futures book: one malformed
    # public level (bad cast, missing field) must be skipped individually, not
    # discard the whole gate x perp block. Pre-fix the raw comprehension raised
    # on the first bad row and lost every level.
    connector = _gate(monkeypatch, {
        "contracts/BTC_USDT": {"quanto_multiplier": str(MULT)},
        "futures/usdt/order_book": {
            "current": 1783852195359,
            "bids": [
                {"s": 7490, "p": "63860.6"},
                {"s": 5000, "p": "oops"},   # cast failure
                {"p": "63855.0"},           # missing size
                {"s": 3000, "p": "63840.0"},
            ],
            "asks": [{"s": 5000, "p": "63870.0"}],
        },
    })

    book = connector.fetch_orderbook("BTC_USDT", "perp_usdt", 5)

    assert [level[0] for level in book.bids] == [63860.6, 63840.0]
    assert book.bids[0] == (63860.6, pytest.approx(7490 * MULT))
    assert book.best_bid == 63860.6 and book.best_ask == 63870.0


def test_gate_perp_open_interest_scaled(monkeypatch) -> None:
    connector = _gate(monkeypatch, {
        "contracts/BTC_USDT": {"quanto_multiplier": str(MULT)},
        "futures/usdt/tickers": [{"contract": "BTC_USDT", "total_size": "631215512", "funding_rate": "0.000051"}],
    })

    snap = connector.fetch_open_interest("BTC_USDT", "perp_usdt")

    assert snap.open_interest_base == pytest.approx(631215512 * MULT)


def test_gate_funding(monkeypatch) -> None:
    connector = _gate(monkeypatch, {
        "futures/usdt/funding_rate": [{"r": "0.000047", "t": 1783843201}],
    })

    snap = connector.fetch_funding("BTC_USDT", "perp_usdt")

    assert snap.funding_rate == pytest.approx(0.000047)
    assert snap.timestamp_ms == 1783843201000


def test_gate_multiplier_fetched_once(monkeypatch) -> None:
    calls = {"contracts": 0}
    connector = GateConnector()

    def fake_get(url: str, params: dict | None = None):
        if "contracts/" in url:
            calls["contracts"] += 1
            return {"quanto_multiplier": str(MULT)}
        if "tickers" in url:
            return [{"total_size": "100"}]
        if "funding_rate" in url:
            return [{"r": "0", "t": 1}]
        raise AssertionError(url)

    monkeypatch.setattr(connector, "_get", fake_get)
    connector.fetch_open_interest("BTC_USDT", "perp_usdt")
    connector.fetch_open_interest("BTC_USDT", "perp_usdt")
    assert calls["contracts"] == 1


def test_gate_unsupported_timeframe(monkeypatch) -> None:
    connector = _gate(monkeypatch, {"spot/candlesticks": []})
    with pytest.raises(UnsupportedTimeframeError, match="TIMEFRAME_UNSUPPORTED"):
        connector.fetch_ohlcv("BTC_USDT", "spot_usdt", "2h", 1)
