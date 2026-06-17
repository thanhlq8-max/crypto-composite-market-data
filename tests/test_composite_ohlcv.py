from __future__ import annotations

from crypto_composite.engines.composite_ohlcv import build_composite_ohlcv, context_to_dict
from crypto_composite.schemas import OHLCVBar


def test_composite_ohlcv_aligns_by_timestamp_and_reports_coverage() -> None:
    raw = {
        "asset": "BTC-USDT",
        "timeframe": "15m",
        "venues": ["binance", "okx", "bybit"],
        "data": {
            "ohlcv": [
                OHLCVBar("binance", "spot_usdt", "BTCUSDT", "15m", 1000, 100, 110, 90, 104, 2, 208, 10, 0.95),
                OHLCVBar("okx", "spot_usdt", "BTC-USDT", "15m", 1000, 101, 111, 91, 106, 1, 106, None, 0.90),
                OHLCVBar("bybit", "spot_usdt", "BTCUSDT", "15m", 2000, 106, 112, 105, 110, 3, 330, None, 0.85),
            ]
        },
    }

    ctx = context_to_dict(build_composite_ohlcv(raw, raw["venues"]))
    bars = ctx["bars_by_market_type"]["spot_usdt"]

    assert len(bars) == 2
    assert bars[0]["timestamp_ms"] == 1000
    assert bars[0]["venue_count"] == 2
    assert bars[0]["coverage"] == 0.666667
    assert bars[0]["median_close"] == 105.0
    assert ctx["status_by_market_type"]["spot_usdt"] in {
        "COMPOSITE_DATA_OK",
        "COMPOSITE_DATA_PARTIAL",
        "COMPOSITE_DATA_WEAK",
    }
