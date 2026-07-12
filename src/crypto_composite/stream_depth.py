"""Measure public depth-zone lifecycle from venue WebSocket book streams.

REST snapshots can only proxy persistence (BUG_MEMORY B1 lineage): between
two scans a depth wall may have lived continuously or flickered. This module
watches the public book streams of the perp-capable venues for a bounded
duration and records, per composite price bucket, how long depth was actually
present — first/last seen, accumulated uptime, refill count, and depth peaks.

Boundaries: observed public snapshots only. The lifecycle artifact describes
depth presence over the watch window; it makes no hidden-liquidity,
market-maker-intent, or future-behavior claim and emits no trading signal.

The `websockets` dependency ships as the optional `[stream]` extra:

    pip install crypto-composite-market-data[stream]
    crypto-composite stream-depth --asset BTC-USDT --duration 120 --out-dir artifacts
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from crypto_composite.connectors.okx import OKXConnector
from crypto_composite.engines.composite_orderbook_ladder import _default_bucket_size
from crypto_composite.symbol_map import resolve_symbol
from crypto_composite.utils import now_ms, write_json

STREAM_MARKET_TYPE = "perp_usdt"
STREAM_VENUES = ("binance", "okx", "bybit")
REFERENCE_BAND_FRACTION = 0.025  # match the REST ladder's actionable band
RECONNECT_BACKOFF_S = 2.0
MAX_RECONNECTS_PER_VENUE = 5
# Long-run memory bounds: a bucket absent this long is dropped, and the total
# bucket count per asset is capped (oldest currently-absent dropped first).
MAX_BUCKETS_PER_ASSET = 4000
PRUNE_ABSENT_MS = 600_000

NO_SIGNAL_BOUNDARY = (
    "Observed public depth lifecycle only; no trading signal, prediction, execution "
    "instruction, hidden-liquidity or market-maker-intent claim."
)


class StreamDependencyError(RuntimeError):
    """Raised when the optional websockets dependency is not installed."""


def _load_websockets():
    try:
        import websockets  # noqa: PLC0415 - optional dependency, imported lazily
    except ImportError as exc:
        raise StreamDependencyError(
            "STREAM_DEPENDENCY_MISSING: websockets is required for stream-depth; "
            "install with: pip install crypto-composite-market-data[stream]"
        ) from exc
    return websockets


# ---------------------------------------------------------------------------
# Frame parsing: one normalized shape per venue frame.
# ---------------------------------------------------------------------------

def _levels(raw: Any, scale: float = 1.0) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for level in raw or []:
        try:
            price = float(level[0])
            size = float(level[1]) * scale
        except (TypeError, ValueError, IndexError):
            continue
        if price > 0:
            out.append((price, size))
    return out


def parse_binance_frame(payload: dict[str, Any]) -> dict[str, list[tuple[float, float]]] | None:
    """fstream partial book depth: bids under 'b'/'bids', asks under 'a'/'asks'."""
    bids = payload.get("b") if payload.get("b") is not None else payload.get("bids")
    asks = payload.get("a") if payload.get("a") is not None else payload.get("asks")
    if bids is None and asks is None:
        return None
    return {"bids": _levels(bids), "asks": _levels(asks), "type": "snapshot"}


def parse_okx_frame(payload: dict[str, Any], contract_value: float) -> dict[str, list[tuple[float, float]]] | None:
    """OKX books5 channel: data[0] carries full 5-level snapshots in contracts."""
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return None
    book = data[0]
    return {
        "bids": _levels(book.get("bids"), scale=contract_value),
        "asks": _levels(book.get("asks"), scale=contract_value),
        "type": "snapshot",
    }


def parse_bybit_frame(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Bybit v5 orderbook channel: snapshot then deltas (size 0 deletes)."""
    if "data" not in payload or "type" not in payload:
        return None
    book = payload["data"]
    return {
        "bids": _levels(book.get("b")),
        "asks": _levels(book.get("a")),
        "type": "snapshot" if payload["type"] == "snapshot" else "delta",
    }


class VenueBook:
    """Minimal price->size book state; deltas with size 0 remove the level."""

    def __init__(self, venue: str) -> None:
        self.venue = venue
        self.bids: dict[float, float] = {}
        self.asks: dict[float, float] = {}
        self.frames = 0

    def apply(self, frame: dict[str, Any]) -> None:
        if frame["type"] == "snapshot":
            self.bids = {price: size for price, size in frame["bids"] if size > 0}
            self.asks = {price: size for price, size in frame["asks"] if size > 0}
        else:
            for side, levels in ((self.bids, frame["bids"]), (self.asks, frame["asks"])):
                for price, size in levels:
                    if size <= 0:
                        side.pop(price, None)
                    else:
                        side[price] = size
        self.frames += 1

    def mid(self) -> float | None:
        if not self.bids or not self.asks:
            return None
        return (max(self.bids) + min(self.asks)) / 2


# ---------------------------------------------------------------------------
# Lifecycle tracking across venues.
# ---------------------------------------------------------------------------

@dataclass
class BucketLife:
    side: str
    price_low: float
    price_high: float
    first_seen_ms: int
    last_seen_ms: int
    observed_ms: int = 0
    refill_count: int = 0
    present: bool = True
    absent_since_ms: int | None = None
    max_depth_quote: float = 0.0
    depth_quote_sum: float = 0.0
    samples: int = 0
    max_venue_count: int = 0
    last_sample_ms: int = field(default=0)


class LifecycleTracker:
    """Aggregate venue books into price buckets and time their presence."""

    def __init__(self, reference_price: float, bucket_size: float) -> None:
        self.reference_price = float(reference_price)
        self.bucket_size = float(bucket_size)
        self.buckets: dict[tuple[str, float], BucketLife] = {}
        self.samples = 0

    def _bucket_low(self, price: float) -> float:
        return round((price // self.bucket_size) * self.bucket_size, 10)

    def sample(self, books: list[VenueBook], at_ms: int | None = None) -> None:
        """Fold the current cross-venue state into the lifecycle counters."""
        now = at_ms if at_ms is not None else now_ms()
        current: dict[tuple[str, float], dict[str, float]] = {}
        band = self.reference_price * REFERENCE_BAND_FRACTION
        for book in books:
            for side_name, side in (("bid", book.bids), ("ask", book.asks)):
                for price, size in side.items():
                    if size <= 0 or abs(price - self.reference_price) > band:
                        continue
                    key = (side_name, self._bucket_low(price))
                    current.setdefault(key, {})
                    current[key][book.venue] = current[key].get(book.venue, 0.0) + price * size

        for key, venue_depth in current.items():
            depth = sum(venue_depth.values())
            life = self.buckets.get(key)
            if life is None:
                life = BucketLife(
                    side=key[0],
                    price_low=key[1],
                    price_high=round(key[1] + self.bucket_size, 10),
                    first_seen_ms=now,
                    last_seen_ms=now,
                    last_sample_ms=now,
                )
                self.buckets[key] = life
            else:
                if life.present:
                    life.observed_ms += max(now - life.last_sample_ms, 0)
                else:
                    life.refill_count += 1
                    life.present = True
                    life.absent_since_ms = None
                life.last_seen_ms = now
            life.last_sample_ms = now
            life.max_depth_quote = max(life.max_depth_quote, depth)
            life.depth_quote_sum += depth
            life.samples += 1
            life.max_venue_count = max(life.max_venue_count, len(venue_depth))

        for key, life in self.buckets.items():
            if key not in current and life.present:
                life.present = False
                life.absent_since_ms = now
                life.last_sample_ms = now
        self.samples += 1

    def prune(self, now: int, max_buckets: int = MAX_BUCKETS_PER_ASSET,
              max_absent_ms: int = PRUNE_ABSENT_MS) -> int:
        """Bound memory for long runs: drop long-absent buckets, then cap total.

        A pruned bucket that reappears later is counted fresh; over an
        hours-long window a bucket absent for max_absent_ms is effectively
        dead, so this trades tail history for bounded memory.
        """
        dead = [
            key for key, life in self.buckets.items()
            if not life.present and life.absent_since_ms is not None
            and now - life.absent_since_ms > max_absent_ms
        ]
        for key in dead:
            del self.buckets[key]
        pruned = len(dead)
        if len(self.buckets) > max_buckets:
            absent = sorted(
                (key for key, life in self.buckets.items() if not life.present),
                key=lambda key: self.buckets[key].last_seen_ms,
            )
            for key in absent:
                if len(self.buckets) <= max_buckets:
                    break
                del self.buckets[key]
                pruned += 1
        return pruned

    def report(self, window_ms: int) -> list[dict[str, Any]]:
        out = []
        for life in self.buckets.values():
            uptime = min(life.observed_ms / window_ms, 1.0) if window_ms > 0 else 0.0
            out.append({
                "side": life.side,
                "price_low": life.price_low,
                "price_high": life.price_high,
                "first_seen_ms": life.first_seen_ms,
                "last_seen_ms": life.last_seen_ms,
                "observed_ms": life.observed_ms,
                "uptime_ratio": round(uptime, 6),
                "refill_count": life.refill_count,
                "max_depth_quote": round(life.max_depth_quote, 2),
                "avg_depth_quote": round(life.depth_quote_sum / max(life.samples, 1), 2),
                "max_venue_count": life.max_venue_count,
                "samples": life.samples,
            })
        out.sort(key=lambda item: (item["side"], item["price_low"]))
        return out


# ---------------------------------------------------------------------------
# Venue stream workers.
# ---------------------------------------------------------------------------

def _binance_endpoint(symbol: str) -> tuple[str, None]:
    return f"wss://fstream.binance.com/ws/{symbol.lower()}@depth20@500ms", None


def _okx_endpoint(symbol: str) -> tuple[str, str]:
    subscribe = json.dumps({"op": "subscribe", "args": [{"channel": "books5", "instId": symbol}]})
    return "wss://ws.okx.com:8443/ws/v5/public", subscribe


def _bybit_endpoint(symbol: str) -> tuple[str, str]:
    subscribe = json.dumps({"op": "subscribe", "args": [f"orderbook.50.{symbol}"]})
    return "wss://stream.bybit.com/v5/public/linear", subscribe


async def _venue_worker(
    websockets_module,
    venue: str,
    symbol: str,
    book: VenueBook,
    stop_at: float,
    notes: list[str],
    contract_value: float,
) -> None:
    endpoint, subscribe = {
        "binance": _binance_endpoint,
        "okx": _okx_endpoint,
        "bybit": _bybit_endpoint,
    }[venue](symbol)
    reconnects = 0
    while time.monotonic() < stop_at and reconnects <= MAX_RECONNECTS_PER_VENUE:
        try:
            async with websockets_module.connect(endpoint, ping_interval=20, ping_timeout=20) as socket:
                if subscribe:
                    await socket.send(subscribe)
                while time.monotonic() < stop_at:
                    remaining = stop_at - time.monotonic()
                    try:
                        raw = await asyncio.wait_for(socket.recv(), timeout=min(remaining, 5.0))
                    except asyncio.TimeoutError:
                        continue
                    try:
                        payload = json.loads(raw)
                    except (TypeError, ValueError):
                        continue
                    if venue == "binance":
                        frame = parse_binance_frame(payload)
                    elif venue == "okx":
                        frame = parse_okx_frame(payload, contract_value)
                    else:
                        frame = parse_bybit_frame(payload)
                    if frame is not None:
                        book.apply(frame)
        except Exception as exc:  # reconnect with backoff; venue stays best-effort
            reconnects += 1
            notes.append(f"{venue}: reconnect {reconnects} after {type(exc).__name__}: {exc}")
            await asyncio.sleep(RECONNECT_BACKOFF_S)
    if reconnects > MAX_RECONNECTS_PER_VENUE:
        notes.append(f"{venue}: gave up after {MAX_RECONNECTS_PER_VENUE} reconnects")


def _artifact_stem(asset: str) -> str:
    return asset.replace("/", "_").replace(" ", "_")


class _AssetStream:
    """Per-asset stream state: venue books, symbols, contract scaling, tracker."""

    def __init__(self, asset: str, venues: list[str]) -> None:
        self.asset = asset
        self.venues = venues
        self.notes: list[str] = []
        self.pruned = 0
        self.started_ms = now_ms()
        self.books: dict[str, VenueBook] = {}
        self.symbols: dict[str, str] = {}
        self.contract_values: dict[str, float] = {}
        self.tracker: LifecycleTracker | None = None
        for venue in venues:
            self.symbols[venue] = resolve_symbol(asset, venue, STREAM_MARKET_TYPE)
            self.books[venue] = VenueBook(venue)
            self.contract_values[venue] = (
                OKXConnector()._contract_value(self.symbols[venue]) if venue == "okx" else 1.0
            )

    def try_start_tracker(self) -> bool:
        if self.tracker is not None:
            return True
        mids = [m for m in (self.books[v].mid() for v in self.venues) if m]
        if not mids:
            return False
        reference = sum(mids) / len(mids)
        self.tracker = LifecycleTracker(reference, _default_bucket_size(reference))
        return True

    def sample(self, now: int) -> None:
        if self.tracker is None:
            return
        self.tracker.sample(list(self.books.values()), at_ms=now)
        self.pruned += self.tracker.prune(now)

    def result(self) -> dict[str, Any]:
        window_ms = now_ms() - self.started_ms
        frames = {venue: self.books[venue].frames for venue in self.venues}
        silent = [venue for venue, count in frames.items() if count == 0]
        notes = list(self.notes)
        if silent:
            notes.append(f"no frames received from: {', '.join(silent)}")
        if self.pruned:
            notes.append(f"pruned {self.pruned} long-absent/overflow buckets during the run")
        return {
            "asset": self.asset,
            "market_type": STREAM_MARKET_TYPE,
            "started_at_ms": self.started_ms,
            "window_ms": window_ms,
            "venues": self.venues,
            "frames_per_venue": frames,
            "samples": self.tracker.samples if self.tracker else 0,
            "reference_price": round(self.tracker.reference_price, 8) if self.tracker else None,
            "bucket_size": self.tracker.bucket_size if self.tracker else None,
            "buckets": self.tracker.report(window_ms) if self.tracker else [],
            "notes": notes,
            "boundaries": [NO_SIGNAL_BOUNDARY],
        }


async def _run_streams(
    websockets_module,
    assets: list[str],
    venues: list[str],
    duration_s: float,
    sample_interval_s: float,
    flush_interval_s: float | None,
    flush_cb=None,
) -> dict[str, dict[str, Any]]:
    streams = {asset: _AssetStream(asset, venues) for asset in assets}
    stop_at = time.monotonic() + duration_s
    workers = [
        asyncio.create_task(
            _venue_worker(
                websockets_module, venue, stream.symbols[venue], stream.books[venue],
                stop_at, stream.notes, stream.contract_values[venue],
            )
        )
        for stream in streams.values()
        for venue in venues
    ]

    last_flush = time.monotonic()
    try:
        while time.monotonic() < stop_at:
            await asyncio.sleep(sample_interval_s)
            now = now_ms()
            for stream in streams.values():
                if stream.try_start_tracker():
                    stream.sample(now)
            if flush_interval_s and flush_cb and time.monotonic() - last_flush >= flush_interval_s:
                flush_cb({asset: s.result() for asset, s in streams.items() if s.tracker})
                last_flush = time.monotonic()
    finally:
        await asyncio.gather(*workers, return_exceptions=True)

    results = {asset: stream.result() for asset, stream in streams.items()}
    if not any(streams[a].tracker for a in assets):
        raise RuntimeError("STREAM_NO_DATA: no venue produced a book mid within the window")
    return results


def run_stream_depth(
    asset: str | None = None,
    venues: list[str] | None = None,
    duration_s: float = 120.0,
    sample_interval_s: float = 1.0,
    out_dir: str | Path = "artifacts",
    assets: list[str] | None = None,
    flush_interval_s: float | None = None,
) -> dict[str, Any]:
    """Watch perp book streams and write zone_lifecycle artifacts.

    Single asset writes zone_lifecycle.json (backward compatible); multiple
    assets write zone_lifecycle_{ASSET}.json each. With flush_interval_s the
    per-asset artifacts are (re)written periodically so a long run is not lost
    if interrupted.
    """
    websockets_module = _load_websockets()
    asset_list = list(assets) if assets else [asset or "BTC-USDT"]
    asset_list = [a.strip() for a in asset_list if a.strip()]
    venue_list = [v.strip().lower() for v in (venues or list(STREAM_VENUES)) if v.strip()]
    unsupported = [v for v in venue_list if v not in STREAM_VENUES]
    if unsupported:
        raise ValueError(
            f"STREAM_VENUE_UNSUPPORTED venues={unsupported!r} supported={','.join(STREAM_VENUES)}"
        )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    multi = len(asset_list) > 1

    def _write(results: dict[str, dict[str, Any]]) -> None:
        for asset_name, result in results.items():
            name = f"zone_lifecycle_{_artifact_stem(asset_name)}.json" if multi else "zone_lifecycle.json"
            write_json(out / name, result)

    results = asyncio.run(
        _run_streams(
            websockets_module, asset_list, venue_list, float(duration_s),
            float(sample_interval_s), float(flush_interval_s) if flush_interval_s else None, _write,
        )
    )
    _write(results)
    if not multi:
        return results[asset_list[0]]
    return {
        "assets": asset_list,
        "market_type": STREAM_MARKET_TYPE,
        "venues": venue_list,
        "results": results,
        "boundaries": [NO_SIGNAL_BOUNDARY],
    }
