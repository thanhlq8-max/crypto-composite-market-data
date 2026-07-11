from __future__ import annotations

from pathlib import Path

from crypto_composite.engines.composite_ohlcv import build_composite_ohlcv, context_to_dict
from crypto_composite.engines.composite_orderbook_ladder import build_composite_orderbook_ladder
from crypto_composite.pipeline import run_composite
from crypto_composite.schemas import DataQualityReport, OHLCVBar, OrderBookSnapshot
from crypto_composite.symbol_map import venue_supports_market_type
from crypto_composite.utils import now_ms


FIVE_VENUES = ["binance", "okx", "bybit", "coinbase", "kraken"]


def _bar(venue: str, mt: str, ts: int, close: float = 100.0) -> OHLCVBar:
    return OHLCVBar(venue, mt, "BTCUSDT", "15m", ts, close, close + 1, close - 1, close, 1.0, close, None, 0.90)


def test_venue_supports_market_type_excludes_spot_only_venues_from_perp() -> None:
    assert venue_supports_market_type("binance", "perp_usdt")
    assert not venue_supports_market_type("coinbase", "perp_usdt")
    assert not venue_supports_market_type("kraken", "perp_usdt")
    assert venue_supports_market_type("kraken", "spot_usdt")
    # Unknown venues stay conservative (counted in expectations).
    assert venue_supports_market_type("customvenue", "perp_usdt")


def test_perp_coverage_not_penalized_by_spot_only_expected_venues() -> None:
    ts = 1000
    raw = {
        "asset": "BTC-USDT",
        "timeframe": "15m",
        "venues": FIVE_VENUES,
        "data": {"ohlcv": [_bar("binance", "perp_usdt", ts), _bar("okx", "perp_usdt", ts), _bar("bybit", "perp_usdt", ts)]},
    }
    ctx = context_to_dict(build_composite_ohlcv(raw, FIVE_VENUES))
    assert ctx["coverage_by_market_type"]["perp_usdt"] == 1.0
    assert ctx["status_by_market_type"]["perp_usdt"] == "COMPOSITE_DATA_OK"


def test_ladder_perp_coverage_uses_market_type_capable_venues() -> None:
    books = [
        OrderBookSnapshot("binance", "perp_usdt", "BTCUSDT", 1000, [(100.0, 1.0)], [(101.0, 1.0)], 100.0, 101.0, 100.5, 1.0, 1, 0.9),
        OrderBookSnapshot("okx", "perp_usdt", "BTC-USDT-SWAP", 1000, [(100.0, 1.0)], [(101.0, 1.0)], 100.0, 101.0, 100.5, 1.0, 1, 0.9),
    ]
    raw = {"asset": "BTC-USDT", "venues": FIVE_VENUES, "data": {"orderbooks": books}}
    ladders = build_composite_orderbook_ladder(raw, reference_price=100.5, expected_venues=FIVE_VENUES, bucket_size=1.0)
    # 2 of 3 perp-capable venues, not 2 of 5 (which would be 0.4 => WEAK).
    assert ladders["perp_usdt"].coverage == round(2 / 3, 6)
    assert ladders["perp_usdt"].status == "COMPOSITE_BOOK_PARTIAL"


def test_status_uses_last_closed_bar_not_in_progress_candle() -> None:
    closed_ts = 1000  # far past => closed
    open_ts = now_ms()  # bar just opened => in progress
    raw = {
        "asset": "BTC-USDT",
        "timeframe": "15m",
        "venues": ["binance", "okx", "bybit"],
        "data": {
            "ohlcv": [
                _bar("binance", "spot_usdt", closed_ts, 100.0),
                _bar("okx", "spot_usdt", closed_ts, 100.02),
                _bar("bybit", "spot_usdt", closed_ts, 100.01),
                _bar("binance", "spot_usdt", open_ts, 100.0),  # single-venue unclosed bar
            ]
        },
    }
    ctx = context_to_dict(build_composite_ohlcv(raw, raw["venues"]))
    bars = ctx["bars_by_market_type"]["spot_usdt"]
    assert bars[0]["is_closed"] is True
    assert bars[-1]["is_closed"] is False
    # Latest bar stays the freshest bar, but status is judged on the closed bar.
    assert ctx["latest_by_market_type"]["spot_usdt"]["timestamp_ms"] == open_ts
    assert ctx["status_by_market_type"]["spot_usdt"] == "COMPOSITE_DATA_OK"
    assert "status_basis=closed_bar" in " ".join(ctx["notes"])


def _fake_scan_factory():
    def fake_scan(asset: str, venues: list[str], market_types: list[str], timeframe: str, limit: int, depth: int = 100) -> dict:
        return {
            "asset": asset,
            "generated_at_ms": 123,
            "phase": "PHASE_1_DATA_FOUNDATION",
            "venues": venues,
            "timeframe": timeframe,
            "market_types": market_types,
            "data": {
                "ohlcv": [
                    _bar("binance", "spot_usdt", 1000),
                    _bar("okx", "spot_usdt", 1000),
                ],
                "trades": [],
                "orderbooks": [
                    OrderBookSnapshot("binance", "spot_usdt", "BTCUSDT", 1000, [(100.0, 1.0)], [(101.0, 1.0)], 100.0, 101.0, 100.5, 1.0, 1, 0.9),
                    OrderBookSnapshot("okx", "spot_usdt", "BTC-USDT", 1000, [(100.2, 1.0)], [(100.9, 1.0)], 100.2, 100.9, 100.55, 0.7, 1, 0.9),
                ],
                "funding": [],
                "open_interest": [],
            },
            "errors": [],
            "quality_report": DataQualityReport(asset, venues, venues, [], market_types, timeframe, [], 0.9, "OK"),
        }

    return fake_scan


def test_ladder_persistence_carries_over_between_pipeline_runs(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("crypto_composite.pipeline.scan", _fake_scan_factory())
    kwargs = dict(
        asset="BTC-USDT",
        venues=["binance", "okx"],
        market_types=["spot_usdt"],
        timeframes=["15m"],
        limit=10,
        depth=5,
        out_dir=tmp_path,
        bucket_size=1.0,
    )
    first = run_composite(**kwargs)["composite_orderbook_by_timeframe"]["15m"]["spot_usdt"]
    second = run_composite(**kwargs)["composite_orderbook_by_timeframe"]["15m"]["spot_usdt"]

    def _by_key(ladder: dict) -> dict:
        return {
            (lvl["side"], lvl["price_low"]): lvl["persistence"]
            for side in ("bid_levels", "ask_levels")
            for lvl in ladder[side]
        }

    p1 = _by_key(first)
    p2 = _by_key(second)
    assert p1.keys() == p2.keys() and p1
    # Second run must blend in the previous persistence: strictly higher, not equal.
    assert all(p2[k] > p1[k] for k in p1), (p1, p2)
