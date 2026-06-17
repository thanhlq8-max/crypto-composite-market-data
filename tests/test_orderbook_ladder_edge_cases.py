from __future__ import annotations

from crypto_composite.engines.composite_orderbook_ladder import build_composite_orderbook_ladder, ladders_to_dict
from crypto_composite.schemas import OrderBookSnapshot


def _book(
    venue: str,
    bids: list[tuple[float, float]],
    asks: list[tuple[float, float]],
    market_type: str = "spot_usdt",
) -> OrderBookSnapshot:
    return OrderBookSnapshot(
        venue=venue,
        market_type=market_type,
        symbol="BTCUSDT" if venue != "okx" else "BTC-USDT",
        timestamp_ms=1000,
        bids=bids,
        asks=asks,
        best_bid=bids[0][0] if bids else 0.0,
        best_ask=asks[0][0] if asks else 0.0,
        mid=100.5,
        spread=1.0,
        depth_levels=max(len(bids), len(asks)),
        data_quality=0.90,
    )


def test_orderbook_ladder_empty_input_returns_no_market_ladders() -> None:
    raw = {"asset": "BTC-USDT", "venues": ["binance", "okx"], "data": {"orderbooks": []}}

    ladders = ladders_to_dict(build_composite_orderbook_ladder(raw, reference_price=100.5, expected_venues=raw["venues"]))

    assert ladders == {}


def test_orderbook_ladder_filters_invalid_and_far_levels() -> None:
    raw = {
        "asset": "BTC-USDT",
        "venues": ["binance"],
        "data": {
            "orderbooks": [
                _book(
                    "binance",
                    bids=[(100.0, 1.0), (99.0, 0.0), (98.0, -1.0), (90.0, 2.0)],
                    asks=[(101.0, 2.0), (102.0, 0.0), (103.0, -1.0), (110.0, 2.0)],
                )
            ]
        },
    }

    ladder = ladders_to_dict(
        build_composite_orderbook_ladder(raw, reference_price=100.5, expected_venues=raw["venues"], bucket_size=1.0)
    )["spot_usdt"]

    assert ladder["bid_depth_total"] == 100.0
    assert ladder["ask_depth_total"] == 202.0
    assert len(ladder["bid_levels"]) == 1
    assert len(ladder["ask_levels"]) == 1


def test_orderbook_ladder_marks_single_venue_against_three_expected_as_weak() -> None:
    raw = {
        "asset": "BTC-USDT",
        "venues": ["binance", "okx", "bybit"],
        "data": {"orderbooks": [_book("binance", bids=[(100.0, 1.0)], asks=[(101.0, 1.0)])]},
    }

    ladder = ladders_to_dict(
        build_composite_orderbook_ladder(raw, reference_price=100.5, expected_venues=raw["venues"], bucket_size=1.0)
    )["spot_usdt"]

    assert ladder["venue_count"] == 1
    assert ladder["coverage"] == 0.333333
    assert ladder["status"] == "COMPOSITE_BOOK_WEAK"


def test_orderbook_ladder_reports_concentration_hhi_for_dominant_venue_bucket() -> None:
    raw = {
        "asset": "BTC-USDT",
        "venues": ["binance", "okx"],
        "data": {
            "orderbooks": [
                _book("binance", bids=[(100.0, 10.0)], asks=[(101.0, 1.0)]),
                _book("okx", bids=[(100.1, 1.0)], asks=[(101.1, 1.0)]),
            ]
        },
    }

    ladder = ladders_to_dict(
        build_composite_orderbook_ladder(raw, reference_price=100.5, expected_venues=raw["venues"], bucket_size=1.0)
    )["spot_usdt"]

    assert ladder["top_bid_wall"]["venue_count"] == 2
    assert ladder["top_bid_wall"]["hhi"] > 0.80
    assert ladder["top_bid_wall"]["venue_depth_quote"]["binance"] > ladder["top_bid_wall"]["venue_depth_quote"]["okx"]


def test_orderbook_ladder_uses_previous_ladder_persistence_for_matching_bucket() -> None:
    raw = {
        "asset": "BTC-USDT",
        "venues": ["binance"],
        "data": {"orderbooks": [_book("binance", bids=[(100.0, 1.0)], asks=[(101.0, 1.0)])]},
    }
    previous = {
        "spot_usdt": {
            "bid_levels": [{"price_low": 100.0, "persistence": 0.80}],
            "ask_levels": [{"price_low": 101.0, "persistence": 0.70}],
        }
    }

    ladder = ladders_to_dict(
        build_composite_orderbook_ladder(
            raw,
            reference_price=100.5,
            expected_venues=raw["venues"],
            bucket_size=1.0,
            previous_ladder=previous,
        )
    )["spot_usdt"]

    assert ladder["top_bid_wall"]["persistence"] > 0.65
    assert ladder["top_ask_wall"]["persistence"] > 0.55
