from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NO_SIGNAL_BOUNDARY = "Artifact validation only; no trading signal, execution instruction, or financial advice."


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

    combined_ohlcv_path = asset_dir / "composite_ohlcv.json"
    _require_mapping(_read_json(combined_ohlcv_path, result), combined_ohlcv_path, result, "COMPOSITE_OHLCV_NOT_OBJECT")

    combined_ladder_path = asset_dir / "composite_orderbook_ladder.json"
    _require_mapping(
        _read_json(combined_ladder_path, result),
        combined_ladder_path,
        result,
        "COMPOSITE_ORDERBOOK_LADDER_NOT_OBJECT",
    )

    for timeframe in timeframes:
        stem = _artifact_stem(timeframe)
        ohlcv_path = asset_dir / f"composite_ohlcv_{stem}.json"
        ladder_path = asset_dir / f"composite_orderbook_ladder_{stem}.json"
        _require_mapping(
            _read_json(ohlcv_path, result),
            ohlcv_path,
            result,
            "COMPOSITE_OHLCV_TIMEFRAME_NOT_OBJECT",
        )
        _require_mapping(
            _read_json(ladder_path, result),
            ladder_path,
            result,
            "COMPOSITE_ORDERBOOK_LADDER_TIMEFRAME_NOT_OBJECT",
        )

    result["assets_checked"] += 1


def _validate_universe(root: Path, summary: dict[str, Any], result: dict[str, Any]) -> None:
    result["mode"] = "universe"
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
