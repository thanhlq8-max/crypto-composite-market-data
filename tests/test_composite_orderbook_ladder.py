from __future__ import annotations

from crypto_composite.engines.composite_orderbook_ladder import build_composite_orderbook_ladder, ladders_to_dict
from crypto_composite.schemas import OrderBookSnapshot


def test_composite_orderbook_ladder_buckets_public_depth() -> None:
    raw = {
        "asset": "BTC-USDT",
        "venues": ["binance", "okx"],
        "data": {
            "orderbooks": [
                OrderBookSnapshot(
                    "binance",
                    "spot_usdt",
                    "BTCUSDT",
                    1000,
                    bids=[(100.0, 2.0), (99.0, 1.0)],
                    asks=[(101.0, 1.5), (102.0, 1.0)],
                    best_bid=100.0,
                    best_ask=101.0,
                    mid=100.5,
                    spread=1.0,
                    depth_levels=2,
                    data_quality=0.9,
                ),
                OrderBookSnapshot(
                    "okx",
                    "spot_usdt",
                    "BTC-USDT",
                    1001,
                    bids=[(100.1, 1.0), (99.2, 2.0)],
                    asks=[(101.2, 2.0), (102.2, 1.0)],
                    best_bid=100.1,
                    best_ask=101.2,
                    mid=100.65,
                    spread=1.1,
                    depth_levels=2,
                    data_quality=0.85,
                ),
            ]
        },
    }

    ladders = ladders_to_dict(build_composite_orderbook_ladder(raw, reference_price=100.5, expected_venues=raw["venues"], bucket_size=1.0))
    ladder = ladders["spot_usdt"]

    assert ladder["status"] == "COMPOSITE_BOOK_OK"
    assert ladder["venue_count"] == 2
    assert ladder["bid_depth_total"] > 0
    assert ladder["ask_depth_total"] > 0
    assert ladder["top_bid_wall"] is not None
    assert ladder["top_ask_wall"] is not None
