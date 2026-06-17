from __future__ import annotations

from crypto_composite.engines.composite_ohlcv import build_composite_ohlcv, context_to_dict
from crypto_composite.schemas import OHLCVBar


def test_composite_ohlcv_accepts_dict_input_and_falls_back_to_quote_volume() -> None:
    raw = {
        "asset": "BTC-USDT",
        "timeframe": "15m",
        "venues": ["binance", "okx", "bybit"],
        "data": {
            "ohlcv": [
                {
                    "venue": "binance",
                    "market_type": "spot_usdt",
                    "symbol": "BTCUSDT",
                    "timeframe": "15m",
                    "timestamp_ms": 1000,
                    "open": 100.0,
                    "high": 110.0,
                    "low": 90.0,
                    "close": 100.0,
                    "volume_base": 2.0,
                    "volume_quote": None,
                    "trade_count": 10,
                    "data_quality": 0.90,
                },
                {
                    "venue": "okx",
                    "market_type": "spot_usdt",
                    "symbol": "BTC-USDT",
                    "timeframe": "15m",
                    "timestamp_ms": 1000,
                    "open": 101.0,
                    "high": 111.0,
                    "low": 91.0,
                    "close": 100.05,
                    "volume_base": 1.0,
                    "volume_quote": 100.0,
                    "trade_count": None,
                    "data_quality": 0.80,
                },
            ]
        },
    }

    ctx = context_to_dict(build_composite_ohlcv(raw, raw["venues"]))
    bar = ctx["bars_by_market_type"]["spot_usdt"][0]

    assert bar["volume_quote_total"] == 300.0
    assert bar["venue_weights"] == {"binance": 0.666667, "okx": 0.333333}
    assert bar["median_close"] == 100.025
    assert ctx["status_by_market_type"]["spot_usdt"] == "COMPOSITE_DATA_PARTIAL"


def test_composite_ohlcv_marks_high_dispersion_as_weak_even_with_full_coverage() -> None:
    raw = {
        "asset": "BTC-USDT",
        "timeframe": "15m",
        "venues": ["binance", "okx", "bybit"],
        "data": {
            "ohlcv": [
                OHLCVBar("binance", "spot_usdt", "BTCUSDT", "15m", 1000, 100, 101, 99, 100, 1, 100, None, 0.90),
                OHLCVBar("okx", "spot_usdt", "BTC-USDT", "15m", 1000, 200, 201, 199, 200, 1, 200, None, 0.90),
                OHLCVBar("bybit", "spot_usdt", "BTCUSDT", "15m", 1000, 300, 301, 299, 300, 1, 300, None, 0.90),
            ]
        },
    }

    ctx = context_to_dict(build_composite_ohlcv(raw, raw["venues"]))

    assert ctx["coverage_by_market_type"]["spot_usdt"] == 1.0
    assert ctx["latest_by_market_type"]["spot_usdt"]["price_dispersion_pct"] == 100.0
    assert ctx["status_by_market_type"]["spot_usdt"] == "COMPOSITE_DATA_WEAK"


def test_composite_ohlcv_preserves_market_type_separation() -> None:
    raw = {
        "asset": "BTC-USDT",
        "timeframe": "15m",
        "venues": ["binance", "okx"],
        "data": {
            "ohlcv": [
                OHLCVBar("binance", "spot_usdt", "BTCUSDT", "15m", 1000, 100, 101, 99, 100, 1, 100, None, 0.90),
                OHLCVBar("okx", "perp_usdt", "BTC-USDT-SWAP", "15m", 1000, 110, 111, 109, 110, 1, 110, None, 0.90),
            ]
        },
    }

    ctx = context_to_dict(build_composite_ohlcv(raw, raw["venues"]))

    assert sorted(ctx["bars_by_market_type"]) == ["perp_usdt", "spot_usdt"]
    assert ctx["bars_by_market_type"]["spot_usdt"][0]["market_type"] == "spot_usdt"
    assert ctx["bars_by_market_type"]["perp_usdt"][0]["market_type"] == "perp_usdt"


def test_composite_ohlcv_empty_input_returns_empty_context() -> None:
    raw = {"asset": "BTC-USDT", "timeframe": "15m", "venues": ["binance"], "data": {"ohlcv": []}}

    ctx = context_to_dict(build_composite_ohlcv(raw, raw["venues"]))

    assert ctx["bars_by_market_type"] == {}
    assert ctx["latest_by_market_type"] == {}
    assert ctx["status_by_market_type"] == {}
    assert ctx["coverage_by_market_type"] == {}
