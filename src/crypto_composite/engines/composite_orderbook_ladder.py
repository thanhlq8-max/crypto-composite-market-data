from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from crypto_composite.schemas import OrderBookSnapshot, CompositeLadderLevel, CompositeOrderBookLadder
from crypto_composite.symbol_map import venue_supports_market_type
from crypto_composite.utils import clamp, now_ms, dataclass_to_dict


def _to_book(x: Any) -> OrderBookSnapshot:
    return x if isinstance(x, OrderBookSnapshot) else OrderBookSnapshot(**x)


def _hhi(values: dict[str, float]) -> float:
    total = sum(max(v, 0.0) for v in values.values())
    if total <= 0:
        return 1.0
    return sum((max(v, 0.0) / total) ** 2 for v in values.values())


def _level_from_bucket(side: str, price_low: float, bucket_size: float, venue_depth: dict[str, float], max_depth: float, previous_lookup: dict[tuple[str, float], dict] | None = None) -> CompositeLadderLevel:
    depth = float(sum(venue_depth.values()))
    venue_count = len([v for v in venue_depth.values() if v > 0])
    hhi = _hhi(venue_depth)
    key = (side, round(price_low, 8))
    prev = previous_lookup.get(key) if previous_lookup else None
    prev_persistence = float(prev.get("persistence", 0.0)) if isinstance(prev, dict) else 0.0
    base_persistence = 0.55 if venue_count >= 2 else 0.35
    persistence = clamp(prev_persistence * 0.65 + base_persistence * 0.35 + min(depth / max(max_depth, 1e-9), 1.0) * 0.15)
    concentration_risk = clamp((hhi - 0.45) / 0.55)
    weak_persistence = clamp((0.55 - persistence) / 0.55)
    spoof = clamp(concentration_risk * 0.40 + weak_persistence * 0.35 + (0.20 if venue_count <= 1 else 0.0))
    vacuum = clamp(1.0 - depth / max(max_depth, 1e-9))
    return CompositeLadderLevel(
        side=side,
        price_low=float(price_low),
        price_high=float(price_low + bucket_size),
        price_mid=float(price_low + bucket_size / 2),
        depth_quote=float(depth),
        venue_count=int(venue_count),
        venue_depth_quote={k: float(v) for k, v in sorted(venue_depth.items())},
        hhi=float(round(hhi, 6)),
        persistence=float(round(persistence, 6)),
        spoof_risk_proxy=float(round(spoof, 6)),
        vacuum_score=float(round(vacuum, 6)),
    )


LEGACY_BUCKET_SIZE = 25.0
BUCKET_REFERENCE_FRACTION = 0.00025


def _default_bucket_size(reference_price: float) -> float:
    """Bucket width ~0.025% of the reference price, rounded to one significant digit.

    The former fixed 25-USD floor assumed BTC-scale prices: at SOL-scale
    references (~76 USD) the whole +/-2.5% ladder band collapsed into a single
    [75, 100] bucket, making per-asset depth zones meaningless (BUG_MEMORY B6).
    """
    if reference_price <= 0:
        return LEGACY_BUCKET_SIZE
    raw = reference_price * BUCKET_REFERENCE_FRACTION
    step = 10.0 ** math.floor(math.log10(raw))
    return max(round(raw / step) * step, step)


def _previous_lookup(previous_ladder: dict | None, market_type: str) -> dict[tuple[str, float], dict]:
    if not previous_ladder:
        return {}
    src = previous_ladder.get(market_type) if isinstance(previous_ladder.get(market_type), dict) else previous_ladder
    out = {}
    for side_key, side_name in (("bid_levels", "bid"), ("ask_levels", "ask")):
        for lvl in src.get(side_key, []) if isinstance(src, dict) else []:
            try:
                out[(side_name, round(float(lvl.get("price_low")), 8))] = lvl
            except Exception:
                continue
    return out


def build_composite_orderbook_ladder(raw: dict, reference_price: float | None = None, expected_venues: list[str] | None = None, bucket_size: float | None = None, previous_ladder: dict | None = None) -> dict[str, CompositeOrderBookLadder]:
    asset = raw.get("asset", "BTC-USDT")
    expected = list(expected_venues or raw.get("venues", []) or [])
    books = [_to_book(x) for x in raw.get("data", {}).get("orderbooks", [])]
    by_mt: dict[str, list[OrderBookSnapshot]] = defaultdict(list)
    for b in books:
        by_mt[b.market_type].append(b)
    out: dict[str, CompositeOrderBookLadder] = {}
    for mt, xs in by_mt.items():
        expected_for_mt = [v for v in expected if venue_supports_market_type(v, mt)]
        expected_n = max(len(expected_for_mt), 1)
        ref = float(reference_price or (sum(b.mid for b in xs) / max(len(xs), 1) if xs else 0.0))
        bsize = float(bucket_size or _default_bucket_size(ref))
        buckets: dict[tuple[str, float], dict[str, float]] = defaultdict(lambda: defaultdict(float))
        venue_set = set()
        for book in xs:
            venue_set.add(book.venue)
            for side_name, levels in (("bid", book.bids), ("ask", book.asks)):
                for px, qty in levels[:100]:
                    px = float(px)
                    qty = float(qty)
                    if px <= 0 or qty <= 0:
                        continue
                    # Keep actionable near-book area; far levels remain raw connector data, not ladder context.
                    if ref > 0 and abs(px - ref) / ref > 0.025:
                        continue
                    # Round the bucket edge: sub-dollar bucket widths otherwise
                    # produce float-noise keys (76.4400000000001) that break
                    # persistence lookups between runs.
                    low = round((px // bsize) * bsize, 10)
                    buckets[(side_name, low)][book.venue] += px * qty
        max_depth = max((sum(v.values()) for v in buckets.values()), default=1.0)
        prev_lookup = _previous_lookup(previous_ladder, mt)
        bid_levels = []
        ask_levels = []
        for (side, low), venue_depth in buckets.items():
            lvl = _level_from_bucket(side, low, bsize, dict(venue_depth), max_depth, prev_lookup)
            if side == "bid":
                bid_levels.append(lvl)
            else:
                ask_levels.append(lvl)
        bid_levels = sorted(bid_levels, key=lambda x: (abs(x.price_mid - ref), -x.depth_quote))[:80]
        ask_levels = sorted(ask_levels, key=lambda x: (abs(x.price_mid - ref), -x.depth_quote))[:80]
        top_bid = max(bid_levels, key=lambda x: x.depth_quote, default=None)
        top_ask = max(ask_levels, key=lambda x: x.depth_quote, default=None)
        bid_total = sum(x.depth_quote for x in bid_levels)
        ask_total = sum(x.depth_quote for x in ask_levels)
        imb = (bid_total - ask_total) / max(bid_total + ask_total, 1e-9)
        coverage = clamp(len(venue_set) / expected_n)
        # Heuristic corroboration gates; basis recorded in docs/STATUS_THRESHOLDS.md.
        if coverage >= 0.67:
            status = "COMPOSITE_BOOK_OK"
        elif coverage >= 0.34:
            status = "COMPOSITE_BOOK_PARTIAL"
        else:
            status = "COMPOSITE_BOOK_WEAK"
        notes = [f"{mt}: coverage={coverage:.2f} venues={sorted(venue_set)}", "public snapshot/stream proxy; not a private matching-engine book"]
        out[mt] = CompositeOrderBookLadder(
            asset=asset,
            market_type=mt,
            generated_at_ms=now_ms(),
            reference_price=ref,
            bucket_size=bsize,
            expected_venues=expected,
            venue_count=len(venue_set),
            coverage=float(round(coverage, 6)),
            bid_levels=bid_levels,
            ask_levels=ask_levels,
            top_bid_wall=top_bid,
            top_ask_wall=top_ask,
            bid_depth_total=float(bid_total),
            ask_depth_total=float(ask_total),
            depth_imbalance=float(round(imb, 6)),
            status=status,
            notes=notes,
        )
    return out


def ladders_to_dict(ladders: dict[str, CompositeOrderBookLadder]) -> dict:
    return {k: dataclass_to_dict(v) for k, v in ladders.items()}
