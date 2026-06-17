from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any

from crypto_composite.schemas import OHLCVBar, CompositeOHLCVBar, CompositeOHLCVContext
from crypto_composite.utils import clamp, now_ms, dataclass_to_dict


def _to_bar(x: Any) -> OHLCVBar:
    return x if isinstance(x, OHLCVBar) else OHLCVBar(**x)


def _weighted(values: list[tuple[float, float]], fallback: float = 0.0) -> float:
    total = sum(max(w, 0.0) for _, w in values)
    if total <= 0:
        return fallback
    return sum(v * max(w, 0.0) for v, w in values) / total


def _qvol(b: OHLCVBar) -> float:
    return float(b.volume_quote if b.volume_quote is not None else b.close * b.volume_base)


def _status(coverage: float, latest_dispersion_pct: float) -> str:
    if coverage >= 0.67 and latest_dispersion_pct <= 0.08:
        return "COMPOSITE_DATA_OK"
    if coverage >= 0.34 and latest_dispersion_pct <= 0.20:
        return "COMPOSITE_DATA_PARTIAL"
    return "COMPOSITE_DATA_WEAK"


def build_composite_ohlcv(raw: dict, expected_venues: list[str] | None = None) -> CompositeOHLCVContext:
    """Build time-aligned composite OHLCV by market type and timestamp.

    This replaces the older append-style multi-venue bar list for downstream zone logic.
    It remains public-data/proxy based; it does not infer true hidden orderflow.
    """
    asset = raw.get("asset", "BTC-USDT")
    timeframe = raw.get("timeframe", "15m")
    expected = list(expected_venues or raw.get("venues", []) or [])
    expected_n = max(len(expected), 1)
    bars = [_to_bar(x) for x in raw.get("data", {}).get("ohlcv", [])]
    grouped: dict[str, dict[int, list[OHLCVBar]]] = defaultdict(lambda: defaultdict(list))
    for b in bars:
        grouped[b.market_type][int(b.timestamp_ms)].append(b)

    bars_by_market: dict[str, list[CompositeOHLCVBar]] = {}
    latest_by_market: dict[str, CompositeOHLCVBar | None] = {}
    status_by_market: dict[str, str] = {}
    coverage_by_market: dict[str, float] = {}
    notes: list[str] = []

    for mt, by_ts in grouped.items():
        comp: list[CompositeOHLCVBar] = []
        for ts in sorted(by_ts):
            xs = by_ts[ts]
            qvols = [_qvol(b) for b in xs]
            total_q = sum(qvols)
            total_b = sum(float(b.volume_base) for b in xs)
            closes = [float(b.close) for b in xs]
            med_close = float(median(closes)) if closes else 0.0
            vwap_close = _weighted([(float(b.close), _qvol(b)) for b in xs], med_close)
            open_w = _weighted([(float(b.open), _qvol(b)) for b in xs], float(xs[0].open))
            high = max(float(b.high) for b in xs)
            low = min(float(b.low) for b in xs)
            venue_depth = defaultdict(float)
            for b in xs:
                venue_depth[b.venue] += _qvol(b)
            weights = {v: round(q / max(total_q, 1e-9), 6) for v, q in sorted(venue_depth.items())}
            venue_count = len(venue_depth)
            coverage = clamp(venue_count / expected_n)
            dispersion = 0.0
            if med_close > 0 and len(closes) > 1:
                dispersion = (max(closes) - min(closes)) / med_close * 100.0
            data_quality = clamp(sum(float(b.data_quality) for b in xs) / max(len(xs), 1) * (0.70 + 0.30 * coverage) - min(dispersion / 1.0, 0.20))
            comp.append(CompositeOHLCVBar(
                asset=asset,
                timeframe=timeframe,
                market_type=mt,
                timestamp_ms=int(ts),
                open=float(open_w),
                high=float(high),
                low=float(low),
                close=float(vwap_close),
                median_close=float(med_close),
                vwap_close=float(vwap_close),
                volume_base_total=float(total_b),
                volume_quote_total=float(total_q),
                venue_count=int(venue_count),
                venue_weights=weights,
                coverage=float(round(coverage, 6)),
                price_dispersion_pct=float(round(dispersion, 6)),
                data_quality=float(round(data_quality, 6)),
            ))
        bars_by_market[mt] = comp
        latest = comp[-1] if comp else None
        latest_by_market[mt] = latest
        cov = float(latest.coverage) if latest else 0.0
        coverage_by_market[mt] = cov
        disp = float(latest.price_dispersion_pct) if latest else 999.0
        status_by_market[mt] = _status(cov, disp)
        if latest:
            notes.append(f"{mt}: {status_by_market[mt]} coverage={cov:.2f} dispersion={disp:.4f}%")
        else:
            notes.append(f"{mt}: COMPOSITE_DATA_WEAK no bars")

    return CompositeOHLCVContext(asset, timeframe, now_ms(), expected, bars_by_market, latest_by_market, status_by_market, coverage_by_market, notes)


def composite_to_raw_ohlcv(context: CompositeOHLCVContext, market_type: str = "spot_usdt") -> list[dict]:
    """Compatibility conversion for legacy functions expecting OHLCVBar-like dicts."""
    out = []
    for b in context.bars_by_market_type.get(market_type, []):
        out.append({
            "venue": "COMPOSITE",
            "market_type": b.market_type,
            "symbol": b.asset,
            "timeframe": b.timeframe,
            "timestamp_ms": b.timestamp_ms,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume_base": b.volume_base_total,
            "volume_quote": b.volume_quote_total,
            "trade_count": None,
            "data_quality": b.data_quality,
            "composite_coverage": b.coverage,
            "price_dispersion_pct": b.price_dispersion_pct,
            "venue_weights": b.venue_weights,
        })
    return out


def context_to_dict(context: CompositeOHLCVContext) -> dict:
    return dataclass_to_dict(context)
