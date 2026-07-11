"""Price zone map: historical reaction bands, insights, and snapshot wiring."""

from __future__ import annotations

import json
from pathlib import Path

from crypto_composite.dashboard_analytics import (
    PRICE_ZONE_MAP_DISCLAIMER,
    _previous_closed_bar_delta,
    _price_zone_map,
    _reaction_zones,
    _swing_points,
    build_dashboard_snapshot,
)
from crypto_composite.dashboard_frontend import render_dashboard_html


def test_template_contains_price_zone_map_panel() -> None:
    html = render_dashboard_html()
    assert 'id="price-zone-map"' in html
    assert 'id="pzm-chart"' in html
    assert 'id="pzm-insights"' in html
    assert 'id="pzm-disclaimer"' in html
    assert "renderPriceZoneMap" in html
    assert "price_zone_map" in html


def _bar(ts: int, price: float, is_closed: bool = True, venue_count: int = 3) -> dict:
    return {
        "asset": "BTC-USDT",
        "timeframe": "15m",
        "market_type": "spot_usdt",
        "timestamp_ms": ts,
        "open": price,
        "high": price + 1.0,
        "low": price - 1.0,
        "close": price,
        "coverage": 1.0,
        "price_dispersion_pct": 0.04,
        "venue_count": venue_count,
        "volume_quote_total": 1000.0,
        "is_closed": is_closed,
    }


# Triangle wave: swing highs near 110 (bar highs ~111), swing lows near 100.
_WAVE = [105, 108, 110, 108, 105, 102, 100, 102, 105, 108, 110.2, 108, 105, 102, 99.8, 102, 105, 108, 110, 108, 105]


def _wave_bars() -> list[dict]:
    return [_bar(1000 + i * 900_000, price) for i, price in enumerate(_WAVE)]


def test_swing_points_find_local_extrema() -> None:
    points = _swing_points(_wave_bars())
    highs = [p for p in points if p["kind"] == "swing_high"]
    lows = [p for p in points if p["kind"] == "swing_low"]
    assert {round(p["price"], 1) for p in highs} == {111.0, 111.2}
    assert {round(p["price"], 1) for p in lows} == {99.0, 98.8}


def test_reaction_zones_cluster_touches_and_report_relation() -> None:
    zones = _reaction_zones(_wave_bars(), reference_price=105.0)
    assert len(zones) == 2
    by_relation = {zone["reference_relation"]: zone for zone in zones}
    upper = by_relation["ABOVE_REFERENCE"]
    lower = by_relation["BELOW_REFERENCE"]
    assert upper["touch_count"] == 3
    assert upper["price_low"] == 111.0 and upper["price_high"] == 111.2
    assert lower["touch_count"] == 2
    assert lower["price_low"] == 98.8 and lower["price_high"] == 99.0
    assert lower["swing_low_count"] == 2 and lower["swing_high_count"] == 0
    assert "historical description" in upper["basis"]


def test_reaction_zones_ignore_unclosed_bars() -> None:
    bars = _wave_bars()
    bars += [_bar(9_000_000 + i * 900_000, price, is_closed=False) for i, price in enumerate([150, 200, 150, 120, 120])]
    zones = _reaction_zones(bars, reference_price=105.0)
    assert all(zone["price_high"] < 130 for zone in zones)


def test_previous_closed_bar_delta_uses_last_two_closed() -> None:
    bars = [_bar(1000, 100.0, venue_count=3), _bar(2000, 101.0, venue_count=2), _bar(3000, 999.0, is_closed=False)]
    delta = _previous_closed_bar_delta(bars)
    assert delta["close_change_pct"] == 1.0
    assert delta["venue_count_previous"] == 3
    assert delta["venue_count_latest"] == 2
    assert delta["timestamp_ms_latest"] == 2000


def test_price_zone_map_assembles_zones_insights_and_disclaimer() -> None:
    bars = _wave_bars()
    ladder = {"reference_price": 105.0, "depth_imbalance": 0.12}
    liquidity = [
        {
            "kind": "BID_LIQUIDITY_CONCENTRATION",
            "side": "bid",
            "price_low": 104.0,
            "price_high": 104.5,
            "depth_quote": 250000.0,
            "venue_count": 3,
        }
    ]
    zone_map = _price_zone_map("15m", "spot_usdt", bars, bars[-1], "COMPOSITE_DATA_OK", ladder, liquidity)
    assert zone_map["reference_price"] == 105.0
    assert zone_map["window"]["closed_bar_count"] == len(bars)
    assert zone_map["window"]["price_low"] == 98.8  # min bar low = 99.8 - 1.0
    assert zone_map["window"]["price_high"] == 111.2  # max bar high = 110.2 + 1.0
    assert len(zone_map["reaction_zones"]) == 2
    assert zone_map["liquidity_zones"] == liquidity
    assert zone_map["disclaimer"] == PRICE_ZONE_MAP_DISCLAIMER
    text = " ".join(zone_map["insights"])
    assert "COMPOSITE_DATA_OK" in text
    assert "Price reacted" in text
    assert "concentration" in text
    assert "imbalance" in text.lower()


def test_snapshot_embeds_price_zone_map(tmp_path: Path) -> None:
    bars = _wave_bars()
    context = {
        "asset": "BTC-USDT",
        "timeframe": "15m",
        "generated_at_ms": 1700000000000,
        "expected_venues": ["binance", "okx", "bybit"],
        "bars_by_market_type": {"spot_usdt": bars},
        "latest_by_market_type": {"spot_usdt": bars[-1]},
        "status_by_market_type": {"spot_usdt": "COMPOSITE_DATA_OK"},
        "coverage_by_market_type": {"spot_usdt": 1.0},
        "notes": [],
    }
    ladder = {
        "asset": "BTC-USDT",
        "market_type": "spot_usdt",
        "generated_at_ms": 1700000000000,
        "reference_price": 105.0,
        "bucket_size": 1.0,
        "expected_venues": ["binance", "okx", "bybit"],
        "venue_count": 3,
        "coverage": 1.0,
        "bid_levels": [],
        "ask_levels": [],
        "top_bid_wall": None,
        "top_ask_wall": None,
        "bid_depth_total": 0.0,
        "ask_depth_total": 0.0,
        "depth_imbalance": 0.0,
        "status": "COMPOSITE_BOOK_OK",
        "notes": [],
    }
    (tmp_path / "run_summary.json").write_text(
        json.dumps({"asset": "BTC-USDT", "timeframes": ["15m"]}), encoding="utf-8"
    )
    (tmp_path / "composite_ohlcv.json").write_text(json.dumps({"15m": context}), encoding="utf-8")
    (tmp_path / "composite_orderbook_ladder.json").write_text(
        json.dumps({"15m": {"spot_usdt": ladder}}), encoding="utf-8"
    )
    (tmp_path / "data_quality.json").write_text(json.dumps({"15m": {"status": "OK"}}), encoding="utf-8")

    snapshot = build_dashboard_snapshot(tmp_path)

    market = snapshot["assets"][0]["timeframes"][0]["markets"][0]
    zone_map = market["price_zone_map"]
    assert zone_map["market_type"] == "spot_usdt"
    assert len(zone_map["reaction_zones"]) == 2
    assert zone_map["disclaimer"] == PRICE_ZONE_MAP_DISCLAIMER
