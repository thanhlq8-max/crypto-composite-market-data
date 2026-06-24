from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from crypto_composite.artifact_validator import validate_artifact_root

NO_SIGNAL_BOUNDARY = "Composite OHLCV CSV export only; no trading signal, execution instruction, or financial advice."

CSV_COLUMNS = (
    "asset",
    "timeframe",
    "market_type",
    "timestamp_ms",
    "open",
    "high",
    "low",
    "close",
    "median_close",
    "vwap_close",
    "volume_base_total",
    "volume_quote_total",
    "venue_count",
    "coverage",
    "price_dispersion_pct",
    "data_quality",
    "venue_weights_json",
)


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _json_cell(value: Any) -> str:
    if not isinstance(value, (dict, list)):
        return ""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _csv_row(
    *,
    asset_label: str | None,
    timeframe_key: str,
    market_type: str,
    context: dict[str, Any],
    bar: dict[str, Any],
) -> dict[str, Any]:
    return {
        "asset": bar.get("asset") or context.get("asset") or asset_label or "",
        "timeframe": bar.get("timeframe") or context.get("timeframe") or timeframe_key,
        "market_type": bar.get("market_type") or market_type,
        "timestamp_ms": bar.get("timestamp_ms", ""),
        "open": bar.get("open", ""),
        "high": bar.get("high", ""),
        "low": bar.get("low", ""),
        "close": bar.get("close", ""),
        "median_close": bar.get("median_close", ""),
        "vwap_close": bar.get("vwap_close", ""),
        "volume_base_total": bar.get("volume_base_total", ""),
        "volume_quote_total": bar.get("volume_quote_total", ""),
        "venue_count": bar.get("venue_count", ""),
        "coverage": bar.get("coverage", ""),
        "price_dispersion_pct": bar.get("price_dispersion_pct", ""),
        "data_quality": bar.get("data_quality", ""),
        "venue_weights_json": _json_cell(bar.get("venue_weights")),
    }


def _asset_rows(asset_dir: Path, asset_label: str | None = None) -> list[dict[str, Any]]:
    combined = _as_mapping(_read_json(asset_dir / "composite_ohlcv.json"))
    rows: list[dict[str, Any]] = []
    for timeframe_key, context_value in sorted(combined.items()):
        context = _as_mapping(context_value)
        bars_by_market_type = _as_mapping(context.get("bars_by_market_type"))
        for market_type, bars_value in sorted(bars_by_market_type.items()):
            for bar_value in _as_list(bars_value):
                bar = _as_mapping(bar_value)
                if bar:
                    rows.append(
                        _csv_row(
                            asset_label=asset_label,
                            timeframe_key=str(timeframe_key),
                            market_type=str(market_type),
                            context=context,
                            bar=bar,
                        )
                    )
    return rows


def _universe_rows(root: Path) -> tuple[list[dict[str, Any]], int]:
    summary = _as_mapping(_read_json(root / "universe_summary.json"))
    asset_results = _as_mapping(summary.get("asset_results"))
    rows: list[dict[str, Any]] = []
    assets_checked = 0
    for asset, item_value in sorted(asset_results.items()):
        item = _as_mapping(item_value)
        if item.get("error"):
            continue
        artifact_dir = item.get("artifact_dir")
        if not isinstance(artifact_dir, str) or not artifact_dir.strip():
            continue
        asset_rows = _asset_rows(root / artifact_dir, str(asset))
        rows.extend(asset_rows)
        assets_checked += 1
    return rows, assets_checked


def write_composite_ohlcv_csv(artifact_root: str | Path, out_file: str | Path) -> dict[str, Any]:
    """Export generated composite OHLCV artifacts to a flat CSV file.

    The export preserves artifact inspection boundaries. It does not rank assets,
    generate predictions, produce trading signals, or create execution advice.
    """
    root = Path(artifact_root)
    csv_path = Path(out_file)
    validation = validate_artifact_root(root)
    result: dict[str, Any] = {
        "status": "OK",
        "artifact_root": str(root),
        "csv_path": str(csv_path),
        "row_count": 0,
        "assets_checked": 0,
        "errors": [],
        "warnings": [],
        "validation": validation,
        "boundaries": [NO_SIGNAL_BOUNDARY],
    }

    if validation.get("status") == "ERROR":
        result["status"] = "ERROR"
        result["errors"] = list(validation.get("errors", []))
        result["warnings"] = list(validation.get("warnings", []))
        return result

    if validation.get("mode") == "universe":
        rows, assets_checked = _universe_rows(root)
    else:
        rows = _asset_rows(root)
        assets_checked = 1 if rows else 0

    result["row_count"] = len(rows)
    result["assets_checked"] = assets_checked
    result["warnings"] = list(validation.get("warnings", []))
    if not rows:
        result["warnings"].append({"path": str(root / "composite_ohlcv.json"), "code": "NO_COMPOSITE_OHLCV_ROWS_EXPORTED"})

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)

    if validation.get("status") == "WARN" or result["warnings"]:
        result["status"] = "WARN"
    return result