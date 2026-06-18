from __future__ import annotations

from pathlib import Path
from typing import Any

from crypto_composite.pipeline import (
    DEFAULT_DEPTH,
    DEFAULT_LIMIT,
    DEFAULT_MARKET_TYPES,
    DEFAULT_TIMEFRAMES,
    DEFAULT_VENUES,
    run_composite,
)
from crypto_composite.utils import write_json


def asset_slug(asset: str) -> str:
    slug = asset.strip().upper().replace("/", "-").replace(" ", "-")
    return "-".join(part for part in slug.split("-") if part)


def run_universe(
    assets: list[str],
    venues: list[str] | None = None,
    market_types: list[str] | None = None,
    timeframes: list[str] | None = None,
    limit: int = DEFAULT_LIMIT,
    depth: int = DEFAULT_DEPTH,
    out_dir: str | Path = "artifacts",
    bucket_size: float | None = None,
) -> dict[str, Any]:
    """Run composite artifact generation for a small explicit asset universe.

    This is a data-quality and artifact orchestration layer. It does not rank assets as
    buy/sell candidates and does not emit execution instructions.
    """
    if not assets:
        raise ValueError("ASSET_UNIVERSE_EMPTY")

    venues = list(venues or DEFAULT_VENUES)
    market_types = list(market_types or DEFAULT_MARKET_TYPES)
    timeframes = list(timeframes or DEFAULT_TIMEFRAMES)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    asset_results: dict[str, Any] = {}
    errors: list[dict[str, str]] = []

    for asset in assets:
        asset_key = asset_slug(asset)
        asset_dir = out / asset_key
        try:
            result = run_composite(
                asset=asset,
                venues=venues,
                market_types=market_types,
                timeframes=timeframes,
                limit=limit,
                depth=depth,
                out_dir=asset_dir,
                bucket_size=bucket_size,
            )
            summary = result["summary"]
            asset_results[asset] = {
                "artifact_dir": asset_key,
                "timeframes": summary["timeframes"],
                "data_quality_by_timeframe": summary.get("data_quality_by_timeframe", {}),
                "outputs": summary.get("outputs", {}),
            }
        except Exception as exc:
            errors.append({"asset": asset, "error": str(exc)})
            asset_results[asset] = {"artifact_dir": asset_key, "error": str(exc)}

    summary = {
        "assets": assets,
        "venues": venues,
        "market_types": market_types,
        "timeframes": timeframes,
        "asset_count": len(assets),
        "asset_results": asset_results,
        "errors": errors,
        "outputs": {
            "universe_summary": "universe_summary.json",
            "per_asset_artifacts": {asset: asset_results[asset].get("artifact_dir") for asset in assets},
        },
        "limitations": [
            "Explicit asset list only; no automatic listing discovery in this release.",
            "Artifacts are data-quality context, not trading recommendations.",
            "No buy/sell ranking, order execution, position sizing, or profitability claim is generated.",
        ],
    }
    write_json(out / "universe_summary.json", summary)
    return summary
