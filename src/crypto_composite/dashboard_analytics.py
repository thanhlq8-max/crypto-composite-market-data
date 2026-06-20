from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EVIDENCE_METHOD = {
    "CORROBORATED": (
        "Book status is OK, at least two venues contribute, and no venue supplies a majority of bucket depth."
    ),
    "CONCENTRATED": "One venue supplies more than half of the observed bucket depth.",
    "LIMITED": "Book coverage is partial/weak or fewer than two venues contribute to the bucket.",
}


def _read_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else None


def _asset_roots(root: Path) -> list[tuple[str | None, Path]]:
    universe = _read_object(root / "universe_summary.json")
    if universe is None:
        return [(None, root)]

    results = universe.get("asset_results")
    if not isinstance(results, dict):
        return []

    resolved: list[tuple[str | None, Path]] = []
    for asset, result in sorted(results.items()):
        if not isinstance(result, dict) or not isinstance(result.get("artifact_dir"), str):
            continue
        candidate = (root / result["artifact_dir"]).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.is_dir():
            resolved.append((str(asset), candidate))
    return resolved


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number == number and number not in (float("inf"), float("-inf")) else None


def _venue_majority_share(level: dict[str, Any]) -> float | None:
    venue_depth = level.get("venue_depth_quote")
    if not isinstance(venue_depth, dict):
        return None
    values = [number for value in venue_depth.values() if (number := _finite_number(value)) is not None and number > 0]
    total = sum(values)
    return max(values) / total if values and total > 0 else None


def _evidence_grade(level: dict[str, Any], ladder: dict[str, Any]) -> tuple[str, float | None]:
    venue_count = level.get("venue_count")
    majority_share = _venue_majority_share(level)
    if ladder.get("status") != "COMPOSITE_BOOK_OK" or not isinstance(venue_count, int) or venue_count < 2:
        return "LIMITED", majority_share
    if majority_share is None or majority_share > 0.5:
        return "CONCENTRATED", majority_share
    return "CORROBORATED", majority_share


def _zone(level: dict[str, Any], ladder: dict[str, Any], kind: str, label: str) -> dict[str, Any]:
    grade, majority_share = _evidence_grade(level, ladder)
    return {
        "kind": kind,
        "label": label,
        "side": level.get("side"),
        "price_low": level.get("price_low"),
        "price_high": level.get("price_high"),
        "price_mid": level.get("price_mid"),
        "depth_quote": level.get("depth_quote"),
        "venue_count": level.get("venue_count"),
        "venue_majority_share": majority_share,
        "hhi": level.get("hhi"),
        "persistence_proxy": level.get("persistence"),
        "spoof_risk_proxy": level.get("spoof_risk_proxy"),
        "vacuum_score": level.get("vacuum_score"),
        "evidence_grade": grade,
        "evidence_definition": EVIDENCE_METHOD[grade],
    }


def _vacuum_level(levels: Any, excluded: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(levels, list):
        return None
    candidates = [
        level
        for level in levels
        if isinstance(level, dict) and _finite_number(level.get("vacuum_score")) is not None
    ]
    if excluded is not None:
        candidates = [
            level
            for level in candidates
            if (level.get("price_low"), level.get("price_high"))
            != (excluded.get("price_low"), excluded.get("price_high"))
        ]
    return max(candidates, key=lambda level: float(level["vacuum_score"]), default=None)


def _observed_zones(ladder: dict[str, Any] | None) -> list[dict[str, Any]]:
    if ladder is None:
        return []
    zones: list[dict[str, Any]] = []
    for side, field, levels_field in (
        ("Bid", "top_bid_wall", "bid_levels"),
        ("Ask", "top_ask_wall", "ask_levels"),
    ):
        wall = ladder.get(field)
        wall = wall if isinstance(wall, dict) else None
        if wall is not None:
            zones.append(
                _zone(
                    wall,
                    ladder,
                    f"{side.upper()}_LIQUIDITY_CONCENTRATION",
                    f"{side} liquidity concentration",
                )
            )
        vacuum = _vacuum_level(ladder.get(levels_field), wall)
        if vacuum is not None:
            zones.append(
                _zone(vacuum, ladder, f"{side.upper()}_PUBLIC_DEPTH_VACUUM", f"{side} public-depth vacuum")
            )
    return zones


def _dislocation(markets: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest = {market.get("market_type"): market.get("latest_bar") for market in markets}
    spot = latest.get("spot_usdt")
    perp = latest.get("perp_usdt")
    if not isinstance(spot, dict) or not isinstance(perp, dict):
        return None
    spot_close = _finite_number(spot.get("close"))
    perp_close = _finite_number(perp.get("close"))
    if spot_close is None or perp_close is None or spot_close <= 0:
        return None
    return {
        "kind": "SPOT_PERP_DISLOCATION_BAND",
        "price_low": min(spot_close, perp_close),
        "price_high": max(spot_close, perp_close),
        "spot_close": spot_close,
        "perp_close": perp_close,
        "basis_pct": (perp_close - spot_close) / spot_close * 100.0,
        "interpretation": "Observed composite close difference; not a convergence forecast.",
    }


def _build_asset(asset_hint: str | None, asset_root: Path, root: Path) -> dict[str, Any] | None:
    ohlcv_by_timeframe = _read_object(asset_root / "composite_ohlcv.json") or {}
    ladder_by_timeframe = _read_object(asset_root / "composite_orderbook_ladder.json") or {}
    quality_by_timeframe = _read_object(asset_root / "data_quality.json") or {}
    run_summary = _read_object(asset_root / "run_summary.json") or {}
    asset = asset_hint or run_summary.get("asset")
    timeframes = sorted(set(ohlcv_by_timeframe) | set(ladder_by_timeframe) | set(quality_by_timeframe))
    if not timeframes:
        return None

    timeframe_rows: list[dict[str, Any]] = []
    for timeframe in timeframes:
        ohlcv = ohlcv_by_timeframe.get(timeframe)
        ohlcv = ohlcv if isinstance(ohlcv, dict) else {}
        ladders = ladder_by_timeframe.get(timeframe)
        ladders = ladders if isinstance(ladders, dict) else {}
        bars_by_market = ohlcv.get("bars_by_market_type")
        bars_by_market = bars_by_market if isinstance(bars_by_market, dict) else {}
        latest_by_market = ohlcv.get("latest_by_market_type")
        latest_by_market = latest_by_market if isinstance(latest_by_market, dict) else {}
        status_by_market = ohlcv.get("status_by_market_type")
        status_by_market = status_by_market if isinstance(status_by_market, dict) else {}
        market_names = sorted(set(bars_by_market) | set(latest_by_market) | set(ladders))
        markets: list[dict[str, Any]] = []
        for market_type in market_names:
            bars = bars_by_market.get(market_type)
            bars = [bar for bar in bars if isinstance(bar, dict)] if isinstance(bars, list) else []
            latest = latest_by_market.get(market_type)
            latest = latest if isinstance(latest, dict) else (bars[-1] if bars else None)
            ladder = ladders.get(market_type)
            ladder = ladder if isinstance(ladder, dict) else None
            markets.append(
                {
                    "market_type": market_type,
                    "generated_at_ms": (
                        ladder.get("generated_at_ms") if ladder is not None else ohlcv.get("generated_at_ms")
                    ),
                    "ohlcv_status": status_by_market.get(market_type),
                    "bars": bars,
                    "latest_bar": latest,
                    "orderbook": ladder,
                    "observed_zones": _observed_zones(ladder),
                }
            )
        quality = quality_by_timeframe.get(timeframe)
        timeframe_rows.append(
            {
                "timeframe": timeframe,
                "quality": quality if isinstance(quality, dict) else None,
                "markets": markets,
                "spot_perp_dislocation": _dislocation(markets),
            }
        )
    return {
        "asset": asset,
        "artifact_path": str(asset_root.relative_to(root)).replace("\\", "/") or ".",
        "timeframes": timeframe_rows,
    }


def build_dashboard_snapshot(artifact_root: str | Path) -> dict[str, Any]:
    """Build a read-only, artifact-derived view for Dashboard V2."""
    root = Path(artifact_root).expanduser().resolve()
    assets = [
        asset
        for hint, path in _asset_roots(root)
        if (asset := _build_asset(hint, path, root)) is not None
    ]
    return {
        "mode": "OBSERVED_PUBLIC_DATA",
        "assets": assets,
        "methodology": {
            "zone_selection": (
                "Top depth bucket and maximum vacuum-score bucket per side; exact duplicate ranges are omitted."
            ),
            "evidence_grades": EVIDENCE_METHOD,
            "snapshot_limit": (
                "Zones describe generated public snapshots. Persistence is an engine proxy, not multi-snapshot "
                "lifecycle proof."
            ),
            "cross_venue_limit": (
                "Price dispersion is shown as a metric; exact disagreement bands are unavailable without per-venue "
                "price bounds in the composite artifact."
            ),
        },
        "boundaries": [
            "Observed public-data context only.",
            "No trading signal, prediction, entry, exit, position sizing, or execution instruction.",
            "No hidden-liquidity, market-maker intent, or future price-reaction claim.",
        ],
    }
