from __future__ import annotations

from pathlib import Path
from typing import Any

from crypto_composite.engines.scan import scan
from crypto_composite.engines.composite_ohlcv import build_composite_ohlcv, context_to_dict
from crypto_composite.engines.composite_orderbook_ladder import build_composite_orderbook_ladder, ladders_to_dict
from crypto_composite.utils import dataclass_to_dict, read_json, write_json

DEFAULT_ASSET = "BTC-USDT"
DEFAULT_VENUES = ["binance", "okx", "bybit"]
DEFAULT_MARKET_TYPES = ["spot_usdt", "perp_usdt"]
DEFAULT_TIMEFRAMES = ["15m"]
DEFAULT_LIMIT = 300
DEFAULT_DEPTH = 100


def latest_composite_price(composite_context: dict[str, Any], preferred_market_type: str = "spot_usdt") -> float | None:
    latest = composite_context.get("latest_by_market_type", {}) or {}
    item = latest.get(preferred_market_type) or latest.get("perp_usdt")
    if isinstance(item, dict) and item.get("close") is not None:
        return float(item["close"])
    return None


def _artifact_stem(timeframe: str) -> str:
    return timeframe.replace("/", "_").replace(" ", "_")


def run_composite(
    asset: str = DEFAULT_ASSET,
    venues: list[str] | None = None,
    market_types: list[str] | None = None,
    timeframes: list[str] | None = None,
    limit: int = DEFAULT_LIMIT,
    depth: int = DEFAULT_DEPTH,
    out_dir: str | Path = "artifacts",
    bucket_size: float | None = None,
) -> dict[str, Any]:
    """Run public market-data scan and composite artifact generation.

    The output is data infrastructure only. It does not emit trading signals,
    orders, position sizing, or financial advice.
    """
    venues = list(venues or DEFAULT_VENUES)
    market_types = list(market_types or DEFAULT_MARKET_TYPES)
    timeframes = list(timeframes or DEFAULT_TIMEFRAMES)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    raw_by_timeframe: dict[str, Any] = {}
    composite_ohlcv_by_timeframe: dict[str, Any] = {}
    composite_orderbook_by_timeframe: dict[str, Any] = {}
    quality_by_timeframe: dict[str, Any] = {}

    previous_ladder: dict[str, Any] | None = None
    previous_path = out / "composite_orderbook_ladder.json"
    if previous_path.exists():
        try:
            previous_ladder = read_json(previous_path)
        except Exception:
            previous_ladder = None

    for timeframe in timeframes:
        stem = _artifact_stem(timeframe)
        raw = scan(asset, venues, market_types, timeframe, limit, depth=depth)
        composite_ohlcv = context_to_dict(build_composite_ohlcv(raw, venues))
        reference_price = latest_composite_price(composite_ohlcv) or 0.0
        composite_ladder = ladders_to_dict(
            build_composite_orderbook_ladder(
                raw,
                reference_price=reference_price,
                expected_venues=venues,
                bucket_size=bucket_size,
                previous_ladder=previous_ladder,
            )
        )

        raw_dict = dataclass_to_dict(raw)
        raw_by_timeframe[timeframe] = raw_dict
        composite_ohlcv_by_timeframe[timeframe] = composite_ohlcv
        composite_orderbook_by_timeframe[timeframe] = composite_ladder
        quality_by_timeframe[timeframe] = dataclass_to_dict(raw.get("quality_report"))

        write_json(out / f"raw_scan_{stem}.json", raw_dict)
        write_json(out / f"composite_ohlcv_{stem}.json", composite_ohlcv)
        write_json(out / f"composite_orderbook_ladder_{stem}.json", composite_ladder)

    summary = {
        "asset": asset,
        "venues": venues,
        "market_types": market_types,
        "timeframes": timeframes,
        "outputs": {
            "raw_scan_by_timeframe": sorted(f"raw_scan_{_artifact_stem(tf)}.json" for tf in timeframes),
            "composite_ohlcv_by_timeframe": sorted(f"composite_ohlcv_{_artifact_stem(tf)}.json" for tf in timeframes),
            "composite_orderbook_ladder_by_timeframe": sorted(f"composite_orderbook_ladder_{_artifact_stem(tf)}.json" for tf in timeframes),
            "combined_composite_ohlcv": "composite_ohlcv.json",
            "combined_composite_orderbook_ladder": "composite_orderbook_ladder.json",
            "data_quality": "data_quality.json",
        },
        "data_quality_by_timeframe": quality_by_timeframe,
        "limitations": [
            "Public exchange endpoints only; no private orderflow.",
            "Composite orderbook ladder is a public snapshot bucket proxy, not a consolidated matching-engine book.",
            "No trading signal, execution instruction, or profitability claim is generated.",
        ],
    }

    write_json(out / "composite_ohlcv.json", composite_ohlcv_by_timeframe)
    write_json(out / "composite_orderbook_ladder.json", composite_orderbook_by_timeframe)
    write_json(out / "data_quality.json", quality_by_timeframe)
    write_json(out / "run_summary.json", summary)

    return {
        "summary": summary,
        "raw_by_timeframe": raw_by_timeframe,
        "composite_ohlcv_by_timeframe": composite_ohlcv_by_timeframe,
        "composite_orderbook_by_timeframe": composite_orderbook_by_timeframe,
    }
