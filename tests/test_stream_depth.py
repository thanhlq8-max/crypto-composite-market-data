"""Zone lifecycle stream: frame parsing, book state, and lifecycle math."""

from __future__ import annotations

import sys

import pytest

from crypto_composite.stream_depth import (
    LifecycleTracker,
    StreamDependencyError,
    VenueBook,
    parse_binance_frame,
    parse_bybit_frame,
    parse_okx_frame,
    run_stream_depth,
)


def test_missing_websockets_raises_dependency_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setitem(sys.modules, "websockets", None)
    with pytest.raises(StreamDependencyError, match="STREAM_DEPENDENCY_MISSING"):
        run_stream_depth(out_dir=tmp_path)


def test_unsupported_stream_venue_rejected(tmp_path) -> None:
    pytest.importorskip("websockets")
    with pytest.raises(ValueError, match="STREAM_VENUE_UNSUPPORTED"):
        run_stream_depth(venues=["binance", "kraken"], out_dir=tmp_path)


def test_parse_binance_frame_accepts_both_field_spellings() -> None:
    short = parse_binance_frame({"b": [["100", "1"]], "a": [["101", "2"]]})
    long = parse_binance_frame({"bids": [["100", "1"]], "asks": [["101", "2"]]})
    assert short == long == {"bids": [(100.0, 1.0)], "asks": [(101.0, 2.0)], "type": "snapshot"}
    assert parse_binance_frame({"e": "ping"}) is None


def test_parse_okx_frame_scales_contracts() -> None:
    frame = parse_okx_frame(
        {"data": [{"bids": [["64000", "190.79"]], "asks": [["64010", "50"]]}]},
        contract_value=0.01,
    )
    assert frame["bids"] == [(64000.0, pytest.approx(1.9079))]
    assert frame["asks"] == [(64010.0, pytest.approx(0.5))]
    assert parse_okx_frame({"event": "subscribe"}, contract_value=0.01) is None


def test_parse_bybit_frame_types() -> None:
    snapshot = parse_bybit_frame({"type": "snapshot", "data": {"b": [["100", "1"]], "a": []}})
    delta = parse_bybit_frame({"type": "delta", "data": {"b": [["100", "0"]], "a": [["101", "3"]]}})
    assert snapshot["type"] == "snapshot"
    assert delta["type"] == "delta"
    assert parse_bybit_frame({"op": "pong"}) is None


def test_venue_book_snapshot_then_delta() -> None:
    book = VenueBook("bybit")
    book.apply({"type": "snapshot", "bids": [(100.0, 1.0), (99.0, 2.0)], "asks": [(101.0, 1.0)]})
    assert book.mid() == pytest.approx(100.5)

    # Delta: remove the 100 bid, add a deeper ask.
    book.apply({"type": "delta", "bids": [(100.0, 0.0)], "asks": [(102.0, 5.0)]})
    assert 100.0 not in book.bids
    assert book.asks[102.0] == 5.0
    assert book.mid() == pytest.approx((99.0 + 101.0) / 2)


def _book_with(venue: str, bids: dict[float, float], asks: dict[float, float]) -> VenueBook:
    book = VenueBook(venue)
    book.bids = dict(bids)
    book.asks = dict(asks)
    return book


def test_lifecycle_tracker_times_presence_and_refills() -> None:
    tracker = LifecycleTracker(reference_price=100.0, bucket_size=1.0)
    present = [_book_with("binance", {100.4: 2.0}, {})]
    absent = [_book_with("binance", {}, {})]

    tracker.sample(present, at_ms=0)       # bucket appears
    tracker.sample(present, at_ms=1000)    # +1000ms observed
    tracker.sample(absent, at_ms=2000)     # disappears
    tracker.sample(present, at_ms=3000)    # refill
    tracker.sample(present, at_ms=4000)    # +1000ms observed

    report = tracker.report(window_ms=4000)
    assert len(report) == 1
    bucket = report[0]
    assert bucket["side"] == "bid"
    assert bucket["price_low"] == 100.0
    assert bucket["observed_ms"] == 2000
    assert bucket["uptime_ratio"] == pytest.approx(0.5)
    assert bucket["refill_count"] == 1
    assert bucket["first_seen_ms"] == 0
    assert bucket["last_seen_ms"] == 4000


def test_lifecycle_tracker_filters_far_prices_and_merges_venues() -> None:
    tracker = LifecycleTracker(reference_price=100.0, bucket_size=1.0)
    books = [
        _book_with("binance", {100.2: 1.0}, {}),
        _book_with("okx", {100.7: 2.0}, {}),
        _book_with("bybit", {150.0: 9.0}, {}),  # outside the 2.5% band
    ]
    tracker.sample(books, at_ms=0)

    report = tracker.report(window_ms=1000)
    assert len(report) == 1
    bucket = report[0]
    # 100.2 and 100.7 land in the same [100, 101) bucket across two venues.
    assert bucket["max_venue_count"] == 2
    assert bucket["max_depth_quote"] == pytest.approx(100.2 * 1.0 + 100.7 * 2.0)


def test_lifecycle_tracker_bucket_edges_align_to_grid() -> None:
    tracker = LifecycleTracker(reference_price=76.46, bucket_size=0.02)
    tracker.sample([_book_with("binance", {76.457: 1.0}, {76.463: 1.0})], at_ms=0)

    report = tracker.report(window_ms=1000)
    lows = {item["price_low"] for item in report}
    assert lows == {76.44, 76.46}
    for item in report:
        assert item["price_high"] == pytest.approx(item["price_low"] + 0.02)
