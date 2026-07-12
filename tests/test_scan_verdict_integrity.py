"""Scan verdicts must reflect what actually happened per venue and market type."""

from __future__ import annotations

import pytest

from crypto_composite.engines import scan as scan_module
from crypto_composite.engines.composite_ohlcv import build_composite_ohlcv, context_to_dict
from crypto_composite.engines.scan import ScanInputError, normalize_venues, scan
from crypto_composite.schemas import OHLCVBar, OrderBookSnapshot, TradePrint


def _bar(venue: str, mt: str, ts: int = 1000) -> OHLCVBar:
    return OHLCVBar(venue, mt, "BTCUSDT", "15m", ts, 100.0, 101.0, 99.0, 100.0, 1.0, 100.0, None, 0.9)


def _trade(venue: str, mt: str) -> TradePrint:
    return TradePrint(venue, mt, "BTCUSDT", 1000, 100.0, 1.0, 100.0, "buy", True, "t1", 0.9)


def _book(venue: str, mt: str) -> OrderBookSnapshot:
    return OrderBookSnapshot(venue, mt, "BTCUSDT", 1000, [(99.0, 1.0)], [(101.0, 1.0)], 99.0, 101.0, 100.0, 2.0, 1, 0.9)


class _FakeConnector:
    """Deterministic connector; per-test class attributes steer behavior."""

    venue = "binance"
    empty_ohlcv = False
    funding_raises = False

    def fetch_ohlcv(self, symbol, mt, timeframe, limit):
        return [] if self.empty_ohlcv else [_bar(self.venue, mt)]

    def fetch_recent_trades(self, symbol, mt, limit):
        return [_trade(self.venue, mt)]

    def fetch_orderbook(self, symbol, mt, depth):
        return _book(self.venue, mt)

    def fetch_funding(self, symbol, mt):
        if self.funding_raises:
            raise RuntimeError("funding endpoint down")
        return None

    def fetch_open_interest(self, symbol, mt):
        return None


@pytest.fixture
def fake_binance(monkeypatch):
    class Fake(_FakeConnector):
        venue = "binance"

    monkeypatch.setitem(scan_module.CONNECTORS, "binance", Fake)
    return Fake


def test_normalize_venues_dedupes_preserving_order() -> None:
    assert normalize_venues(["binance", "Binance", "okx", "BINANCE "]) == ["binance", "okx"]
    with pytest.raises(ScanInputError, match="VENUE_UNSUPPORTED"):
        normalize_venues(["binance", "nope"])


def test_duplicate_venue_input_fetches_once(fake_binance) -> None:
    out = scan("BTC-USDT", ["binance", "Binance"], ["spot_usdt"], "15m", 10, depth=5)

    assert out["venues"] == ["binance"]
    assert len(out["data"]["ohlcv"]) == 1  # not doubled
    assert out["quality_report"].venues_ok == ["binance"]


def test_spot_only_venue_in_perp_run_is_not_a_failure(monkeypatch, fake_binance) -> None:
    class FakeCoinbase(_FakeConnector):
        venue = "coinbase"

    monkeypatch.setitem(scan_module.CONNECTORS, "coinbase", FakeCoinbase)

    out = scan("BTC-USDT", ["binance", "coinbase"], ["perp_usdt"], "15m", 10, depth=5)

    report = out["quality_report"]
    assert report.venues_ok == ["binance"]
    assert report.venues_failed == []  # structurally incapable, not failed
    assert "coinbase:perp_usdt:unsupported_market_type" in report.missing_sources
    assert out["errors"] == []


def test_funding_failure_keeps_market_data_and_degrades_to_missing(fake_binance) -> None:
    fake_binance.funding_raises = True

    out = scan("BTC-USDT", ["binance"], ["perp_usdt"], "15m", 10, depth=5)

    assert len(out["data"]["ohlcv"]) == 1  # bars survived the funding failure
    assert out["errors"] == []
    assert "binance:perp_usdt:funding" in out["quality_report"].missing_sources
    assert out["quality_report"].venues_ok == ["binance"]


def test_zero_record_endpoint_is_recorded_as_missing(fake_binance) -> None:
    fake_binance.empty_ohlcv = True

    out = scan("BTC-USDT", ["binance"], ["spot_usdt"], "15m", 10, depth=5)

    assert "binance:spot_usdt:ohlcv_empty" in out["quality_report"].missing_sources


def test_requested_market_type_without_bars_gets_weak_verdict() -> None:
    raw = {
        "asset": "BTC-USDT",
        "timeframe": "15m",
        "venues": ["binance", "okx", "bybit"],
        "market_types": ["spot_usdt", "perp_usdt"],
        "data": {"ohlcv": [_bar("binance", "spot_usdt"), _bar("okx", "spot_usdt"), _bar("bybit", "spot_usdt")]},
    }

    ctx = context_to_dict(build_composite_ohlcv(raw, ["binance", "okx", "bybit"]))

    assert ctx["status_by_market_type"]["spot_usdt"] == "COMPOSITE_DATA_OK"
    assert ctx["status_by_market_type"]["perp_usdt"] == "COMPOSITE_DATA_WEAK"
    assert ctx["bars_by_market_type"]["perp_usdt"] == []
    assert ctx["latest_by_market_type"]["perp_usdt"] is None
    assert "perp_usdt: COMPOSITE_DATA_WEAK no bars" in ctx["notes"]
