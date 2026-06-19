from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NO_SIGNAL_BOUNDARY = "Artifact validation only; no trading signal, execution instruction, or financial advice."

RUN_SUMMARY_REQUIRED_FIELDS = (
    "asset",
    "venues",
    "market_types",
    "timeframes",
    "outputs",
    "data_quality_by_timeframe",
    "limitations",
)
UNIVERSE_SUMMARY_REQUIRED_FIELDS = (
    "assets",
    "venues",
    "market_types",
    "timeframes",
    "asset_count",
    "asset_results",
    "errors",
    "outputs",
    "limitations",
)
COMPOSITE_OHLCV_REQUIRED_FIELDS = (
    "asset",
    "timeframe",
    "generated_at_ms",
    "expected_venues",
    "bars_by_market_type",
    "latest_by_market_type",
    "status_by_market_type",
    "coverage_by_market_type",
    "notes",
)
COMPOSITE_LADDER_REQUIRED_FIELDS = (
    "asset",
    "market_type",
    "generated_at_ms",
    "reference_price",
    "bucket_size",
    "expected_venues",
    "venue_count",
    "coverage",
    "bid_levels",
    "ask_levels",
    "top_bid_wall",
    "top_ask_wall",
    "bid_depth_total",
    "ask_depth_total",
    "depth_imbalance",
    "status",
    "notes",
)
DATA_QUALITY_REQUIRED_FIELDS = (
    "asset",
    "venues_requested",
    "venues_ok",
    "venues_failed",
    "market_types",
    "timeframe",
    "missing_sources",
    "overall_quality",
    "status",
)
RAW_SCAN_DATA_REQUIRED_FIELDS = (
    "ohlcv",
    "trades",
    "orderbooks",
    "funding",
    "open_interest",
)


def _empty_result(artifact_root: str | Path) -> dict[str, Any]:
    return {
        "status": "OK",
        "artifact_root": str(artifact_root),
        "mode": "unknown",
        "assets_checked": 0,
        "files_checked": 0,
        "errors": [],
        "warnings": [],
        "boundaries": [NO_SIGNAL_BOUNDARY],
    }


def _artifact_stem(timeframe: str) -> str:
    return timeframe.replace("/", "_").replace(" ", "_")


def _read_json(path: Path, result: dict[str, Any]) -> Any | None:
    if not path.exists():
        result["errors"].append({"path": str(path), "code": "MISSING_JSON_FILE"})
        return None
    if not path.is_file():
        result["errors"].append({"path": str(path), "code": "NOT_A_FILE"})
        return None
    result["files_checked"] += 1
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result["errors"].append(
            {
                "path": str(path),
                "code": "INVALID_JSON",
                "message": str(exc),
            }
        )
        return None


def _require_mapping(value: Any, path: Path, result: dict[str, Any], code: str) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        result["errors"].append({"path": str(path), "code": code})
        return None
    return value


def _require_fields(
    value: dict[str, Any],
    path: Path,
    result: dict[str, Any],
    code: str,
    required_fields: tuple[str, ...],
    **context: Any,
) -> bool:
    missing_fields = [field for field in required_fields if field not in value]
    if not missing_fields:
        return True
    error = {"path": str(path), "code": code, "missing_fields": missing_fields}
    error.update(context)
    result["errors"].append(error)
    return False


def _validate_ohlcv_context(value: Any, path: Path, result: dict[str, Any], *, timeframe: str) -> None:
    context = _require_mapping(value, path, result, "COMPOSITE_OHLCV_CONTEXT_NOT_OBJECT")
    if context is not None:
        _require_fields(
            context,
            path,
            result,
            "COMPOSITE_OHLCV_FIELDS_MISSING",
            COMPOSITE_OHLCV_REQUIRED_FIELDS,
            timeframe=timeframe,
        )


def _validate_ladder_document(value: Any, path: Path, result: dict[str, Any], *, timeframe: str) -> None:
    document = _require_mapping(value, path, result, "COMPOSITE_ORDERBOOK_LADDER_NOT_OBJECT")
    if document is None:
        return
    for market_type, ladder_value in document.items():
        ladder = _require_mapping(
            ladder_value,
            path,
            result,
            "COMPOSITE_ORDERBOOK_LADDER_MARKET_TYPE_NOT_OBJECT",
        )
        if ladder is not None:
            _require_fields(
                ladder,
                path,
                result,
                "COMPOSITE_ORDERBOOK_LADDER_FIELDS_MISSING",
                COMPOSITE_LADDER_REQUIRED_FIELDS,
                timeframe=timeframe,
                market_type=market_type,
            )


def _validate_raw_scan_if_present(path: Path, result: dict[str, Any]) -> None:
    if not path.exists():
        return
    raw_scan = _require_mapping(_read_json(path, result), path, result, "RAW_SCAN_NOT_OBJECT")
    if raw_scan is None:
        return
    if not _require_fields(raw_scan, path, result, "RAW_SCAN_FIELDS_MISSING", ("data",)):
        return
    data = _require_mapping(raw_scan.get("data"), path, result, "RAW_SCAN_DATA_NOT_OBJECT")
    if data is not None:
        _require_fields(
            data,
            path,
            result,
            "RAW_SCAN_DATA_FIELDS_MISSING",
            RAW_SCAN_DATA_REQUIRED_FIELDS,
        )


def _validate_single_asset_dir(asset_dir: Path, result: dict[str, Any], asset_label: str | None = None) -> None:
    if not asset_dir.exists():
        result["errors"].append({"path": str(asset_dir), "code": "MISSING_ASSET_DIRECTORY", "asset": asset_label})
        return
    if not asset_dir.is_dir():
        result["errors"].append({"path": str(asset_dir), "code": "ASSET_PATH_NOT_DIRECTORY", "asset": asset_label})
        return

    summary_path = asset_dir / "run_summary.json"
    summary = _require_mapping(_read_json(summary_path, result), summary_path, result, "RUN_SUMMARY_NOT_OBJECT")
    if summary is None:
        return

    _require_fields(
        summary,
        summary_path,
        result,
        "RUN_SUMMARY_FIELDS_MISSING",
        RUN_SUMMARY_REQUIRED_FIELDS,
    )

    timeframes = summary.get("timeframes")
    if not isinstance(timeframes, list) or not all(isinstance(item, str) for item in timeframes):
        result["errors"].append({"path": str(summary_path), "code": "RUN_SUMMARY_TIMEFRAMES_INVALID"})
        return
    if not timeframes:
        result["warnings"].append({"path": str(summary_path), "code": "RUN_SUMMARY_TIMEFRAMES_EMPTY"})

    data_quality_path = asset_dir / "data_quality.json"
    data_quality = _require_mapping(_read_json(data_quality_path, result), data_quality_path, result, "DATA_QUALITY_NOT_OBJECT")
    if data_quality is not None:
        missing_quality = [timeframe for timeframe in timeframes if timeframe not in data_quality]
        if missing_quality:
            result["warnings"].append(
                {
                    "path": str(data_quality_path),
                    "code": "DATA_QUALITY_TIMEFRAME_MISSING",
                    "timeframes": missing_quality,
                }
            )
        for timeframe in timeframes:
            quality_report = data_quality.get(timeframe)
            if not isinstance(quality_report, dict):
                if timeframe in data_quality:
                    result["errors"].append(
                        {
                            "path": str(data_quality_path),
                            "code": "DATA_QUALITY_TIMEFRAME_NOT_OBJECT",
                            "timeframe": timeframe,
                        }
                    )
                continue
            _require_fields(
                quality_report,
                data_quality_path,
                result,
                "DATA_QUALITY_FIELDS_MISSING",
                DATA_QUALITY_REQUIRED_FIELDS,
                timeframe=timeframe,
            )

    combined_ohlcv_path = asset_dir / "composite_ohlcv.json"
    combined_ohlcv = _require_mapping(
        _read_json(combined_ohlcv_path, result),
        combined_ohlcv_path,
        result,
        "COMPOSITE_OHLCV_NOT_OBJECT",
    )
    if combined_ohlcv is not None:
        missing_timeframes = [timeframe for timeframe in timeframes if timeframe not in combined_ohlcv]
        if missing_timeframes:
            result["errors"].append(
                {
                    "path": str(combined_ohlcv_path),
                    "code": "COMPOSITE_OHLCV_TIMEFRAMES_MISSING",
                    "timeframes": missing_timeframes,
                }
            )
        for timeframe in timeframes:
            if timeframe in combined_ohlcv:
                _validate_ohlcv_context(
                    combined_ohlcv[timeframe],
                    combined_ohlcv_path,
                    result,
                    timeframe=timeframe,
                )

    combined_ladder_path = asset_dir / "composite_orderbook_ladder.json"
    combined_ladder = _require_mapping(
        _read_json(combined_ladder_path, result),
        combined_ladder_path,
        result,
        "COMPOSITE_ORDERBOOK_LADDER_NOT_OBJECT",
    )
    if combined_ladder is not None:
        missing_timeframes = [timeframe for timeframe in timeframes if timeframe not in combined_ladder]
        if missing_timeframes:
            result["errors"].append(
                {
                    "path": str(combined_ladder_path),
                    "code": "COMPOSITE_ORDERBOOK_LADDER_TIMEFRAMES_MISSING",
                    "timeframes": missing_timeframes,
                }
            )
        for timeframe in timeframes:
            if timeframe in combined_ladder:
                _validate_ladder_document(
                    combined_ladder[timeframe],
                    combined_ladder_path,
                    result,
                    timeframe=timeframe,
                )

    for timeframe in timeframes:
        stem = _artifact_stem(timeframe)
        raw_scan_path = asset_dir / f"raw_scan_{stem}.json"
        ohlcv_path = asset_dir / f"composite_ohlcv_{stem}.json"
        ladder_path = asset_dir / f"composite_orderbook_ladder_{stem}.json"
        _validate_raw_scan_if_present(raw_scan_path, result)
        _validate_ohlcv_context(_read_json(ohlcv_path, result), ohlcv_path, result, timeframe=timeframe)
        _validate_ladder_document(_read_json(ladder_path, result), ladder_path, result, timeframe=timeframe)

    result["assets_checked"] += 1


def _validate_universe(root: Path, summary: dict[str, Any], result: dict[str, Any]) -> None:
    result["mode"] = "universe"
    _require_fields(
        summary,
        root / "universe_summary.json",
        result,
        "UNIVERSE_SUMMARY_FIELDS_MISSING",
        UNIVERSE_SUMMARY_REQUIRED_FIELDS,
    )
    asset_results = summary.get("asset_results")
    if not isinstance(asset_results, dict):
        result["errors"].append({"path": str(root / "universe_summary.json"), "code": "UNIVERSE_ASSET_RESULTS_INVALID"})
        return
    if not asset_results:
        result["warnings"].append({"path": str(root / "universe_summary.json"), "code": "UNIVERSE_ASSET_RESULTS_EMPTY"})

    for asset, item in asset_results.items():
        if not isinstance(item, dict):
            result["errors"].append(
                {
                    "path": str(root / "universe_summary.json"),
                    "code": "UNIVERSE_ASSET_RESULT_NOT_OBJECT",
                    "asset": asset,
                }
            )
            continue
        if item.get("error"):
            result["warnings"].append(
                {
                    "path": str(root / "universe_summary.json"),
                    "code": "UNIVERSE_ASSET_HAS_ERROR",
                    "asset": asset,
                    "message": str(item.get("error")),
                }
            )
            continue
        artifact_dir = item.get("artifact_dir")
        if not isinstance(artifact_dir, str) or not artifact_dir.strip():
            result["errors"].append(
                {
                    "path": str(root / "universe_summary.json"),
                    "code": "UNIVERSE_ASSET_ARTIFACT_DIR_INVALID",
                    "asset": asset,
                }
            )
            continue
        _validate_single_asset_dir(root / artifact_dir, result, asset_label=asset)


def validate_artifact_root(artifact_root: str | Path) -> dict[str, Any]:
    """Validate generated JSON artifact structure without interpreting it as trading advice."""
    root = Path(artifact_root)
    result = _empty_result(root)

    if not root.exists():
        result["errors"].append({"path": str(root), "code": "ARTIFACT_ROOT_MISSING"})
        result["status"] = "ERROR"
        return result
    if not root.is_dir():
        result["errors"].append({"path": str(root), "code": "ARTIFACT_ROOT_NOT_DIRECTORY"})
        result["status"] = "ERROR"
        return result

    universe_path = root / "universe_summary.json"
    run_summary_path = root / "run_summary.json"

    if universe_path.exists():
        universe_summary = _require_mapping(_read_json(universe_path, result), universe_path, result, "UNIVERSE_SUMMARY_NOT_OBJECT")
        if universe_summary is not None:
            _validate_universe(root, universe_summary, result)
    elif run_summary_path.exists():
        result["mode"] = "single_asset"
        _validate_single_asset_dir(root, result)
    else:
        result["errors"].append(
            {
                "path": str(root),
                "code": "ARTIFACT_ROOT_MISSING_SUMMARY",
                "expected": ["universe_summary.json", "run_summary.json"],
            }
        )

    if result["errors"]:
        result["status"] = "ERROR"
    elif result["warnings"]:
        result["status"] = "WARN"
    else:
        result["status"] = "OK"
    return result
