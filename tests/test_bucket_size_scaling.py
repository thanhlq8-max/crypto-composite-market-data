"""Default ladder bucket width scales with the asset's reference price (B6)."""

from __future__ import annotations

import pytest

from crypto_composite.engines.composite_orderbook_ladder import (
    LEGACY_BUCKET_SIZE,
    _default_bucket_size,
    build_composite_orderbook_ladder,
)
from crypto_composite.schemas import OrderBookSnapshot


@pytest.mark.parametrize(
    "reference,expected",
    [
        (64000.0, 20.0),     # BTC-scale: 16 -> one significant digit
        (3000.0, 0.8),       # ETH-scale: 0.75 -> 0.8
        (76.46, 0.02),       # SOL-scale: 0.0191 -> 0.02
        (0.35, 0.00009),     # sub-dollar: 8.75e-05 -> 9e-05
        (0.0, LEGACY_BUCKET_SIZE),   # no reference: legacy fallback
        (-5.0, LEGACY_BUCKET_SIZE),  # defensive
    ],
)
def test_default_bucket_size_scales_with_reference(reference, expected) -> None:
    assert _default_bucket_size(reference) == pytest.approx(expected)


def _book(venue: str, mid: float) -> OrderBookSnapshot:
    spread = mid * 0.0002
    bids = [(mid - spread * (i + 1), 1.0) for i in range(20)]
    asks = [(mid + spread * (i + 1), 1.0) for i in range(20)]
    return OrderBookSnapshot(
        venue, "spot_usdt", "SOLUSDT", 1000, bids, asks,
        bids[0][0], asks[0][0], mid, asks[0][0] - bids[0][0], 20, 0.9,
    )


def test_low_priced_asset_gets_multiple_buckets_per_side() -> None:
    raw = {
        "asset": "SOL-USDT",
        "venues": ["binance", "okx", "bybit"],
        "data": {"orderbooks": [_book("binance", 76.46), _book("okx", 76.48), _book("bybit", 76.44)]},
    }
    ladder = build_composite_orderbook_ladder(
        raw, reference_price=76.46, expected_venues=["binance", "okx", "bybit"]
    )["spot_usdt"]

    assert ladder.bucket_size == pytest.approx(0.02)
    # Pre-fix the whole book collapsed into one [75, 100] bucket per side.
    assert len(ladder.bid_levels) > 3
    assert len(ladder.ask_levels) > 3
    widths = {round(lvl.price_high - lvl.price_low, 10) for lvl in ladder.bid_levels}
    assert widths == {0.02}


def test_bucket_edges_have_no_float_noise() -> None:
    raw = {
        "asset": "SOL-USDT",
        "venues": ["binance"],
        "data": {"orderbooks": [_book("binance", 76.46)]},
    }
    ladder = build_composite_orderbook_ladder(
        raw, reference_price=76.46, expected_venues=["binance"]
    )["spot_usdt"]
    for lvl in ladder.bid_levels + ladder.ask_levels:
        assert lvl.price_low == round(lvl.price_low, 10)
        assert len(str(lvl.price_low).split(".")[-1]) <= 10


def test_explicit_bucket_size_still_wins() -> None:
    raw = {
        "asset": "SOL-USDT",
        "venues": ["binance"],
        "data": {"orderbooks": [_book("binance", 76.46)]},
    }
    ladder = build_composite_orderbook_ladder(
        raw, reference_price=76.46, expected_venues=["binance"], bucket_size=1.0
    )["spot_usdt"]
    assert ladder.bucket_size == 1.0
