from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crypto_composite.artifact_validator import validate_artifact_root

NO_SIGNAL_BOUNDARY = "Artifact quality scoring only; no trading signal, execution instruction, or financial advice."

_STATUS_SCORE = {
    "OK": 100.0,
    "PARTIAL": 65.0,
    "INSUFFICIENT_DATA": 20.0,
    "COMPOSITE_DATA_OK": 100.0,
    "COMPOSITE_DATA_PARTIAL": 65.0,
    "COMPOSITE_DATA_WEAK": 20.0,
    "COMPOSITE_BOOK_OK": 100.0,
    "COMPOSITE_BOOK_PARTIAL": 65.0,
    "COMPOSITE_BOOK_WEAK": 20.0,
}


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:
        return default
    return number


def _score_status(value: Any, default: float = 0.0) -> float:
    if isinstance(value, str):
        return _STATUS_SCORE.get(value, default)
    return default


def _average(values: list[float], default: float = 0.0) -> float:
    clean = [float(v) for v in values if v == v]
    if not clean:
        return default
    return sum(clean) / len(clean)


def _grade(score: float) -> str:
    if score >= 90.0:
        return "A"
    if score >= 80.0:
        return "B"
    if score >= 65.0:
        return "C"
    if score >= 50.0:
        return "D"
    return "F"


def _dispersion_score(dispersion_pct: float) -> float:
    if dispersion_pct <= 0.08:
        return 100.0
    if dispersion_pct <= 0.20:
        return 70.0
    if dispersion_pct <= 0.50:
        return 40.0
    return 15.0


def _market_values(mapping: Any) -> list[Any]:
    if isinstance(mapping, dict):
        return list(mapping.values())
    return []


def _score_single_asset(asset_dir: Path, asset_name: str | None = None) -> dict[str, Any]:
    run_summary = _read_json(asset_dir / "run_summary.json") or {}
    data_quality = _read_json(asset_dir / "data_quality.json") or {}
    composite_ohlcv = _read_json(asset_dir / "composite_ohlcv.json") or {}
    composite_ladder = _read_json(asset_dir / "composite_orderbook_ladder.json") or {}

    timeframes = run_summary.get("timeframes") if isinstance(run_summary, dict) else None
    if not isinstance(timeframes, list):
        timeframes = sorted(set(data_quality.keys())) if isinstance(data_quality, dict) else []

    timeframe_scores: dict[str, Any] = {}
    warnings: list[dict[str, Any]] = []

    for timeframe in timeframes:
        quality = data_quality.get(timeframe, {}) if isinstance(data_quality, dict) else {}
        ohlcv = composite_ohlcv.get(timeframe, {}) if isinstance(composite_ohlcv, dict) else {}
        ladder = composite_ladder.get(timeframe, {}) if isinstance(composite_ladder, dict) else {}

        venues_requested = quality.get("venues_requested", []) if isinstance(quality, dict) else []
        venues_ok = quality.get("venues_ok", []) if isinstance(quality, dict) else []
        venue_coverage = 0.0
        if isinstance(venues_requested, list) and venues_requested:
            venue_coverage = min(len(venues_ok) / max(len(venues_requested), 1), 1.0) * 100.0

        scan_quality = _as_float(quality.get("overall_quality") if isinstance(quality, dict) else None, 0.0) * 100.0
        scan_status_score = _score_status(quality.get("status") if isinstance(quality, dict) else None, 0.0)

        coverage_by_market = ohlcv.get("coverage_by_market_type", {}) if isinstance(ohlcv, dict) else {}
        ohlcv_coverage_score = _average([_as_float(v) * 100.0 for v in _market_values(coverage_by_market)], 0.0)

        ohlcv_status_map = ohlcv.get("status_by_market_type", {}) if isinstance(ohlcv, dict) else {}
        ohlcv_status_score = _average([_score_status(v) for v in _market_values(ohlcv_status_map)], 0.0)

        latest_by_market = ohlcv.get("latest_by_market_type", {}) if isinstance(ohlcv, dict) else {}
        dispersion_scores: list[float] = []
        if isinstance(latest_by_market, dict):
            for latest in latest_by_market.values():
                if isinstance(latest, dict):
                    dispersion_scores.append(_dispersion_score(_as_float(latest.get("price_dispersion_pct"), 999.0)))
        dispersion_score = _average(dispersion_scores, 0.0)

        book_coverages: list[float] = []
        book_status_scores: list[float] = []
        if isinstance(ladder, dict):
            for market_ladder in ladder.values():
                if isinstance(market_ladder, dict):
                    book_coverages.append(_as_float(market_ladder.get("coverage"), 0.0) * 100.0)
                    book_status_scores.append(_score_status(market_ladder.get("status"), 0.0))
        book_coverage_score = _average(book_coverages, 0.0)
        book_status_score = _average(book_status_scores, 0.0)

        score = (
            scan_quality * 0.20
            + scan_status_score * 0.10
            + venue_coverage * 0.10
            + ohlcv_coverage_score * 0.20
            + ohlcv_status_score * 0.15
            + dispersion_score * 0.05
            + book_coverage_score * 0.10
            + book_status_score * 0.10
        )
        score = round(max(0.0, min(100.0, score)), 2)
        grade = _grade(score)

        if grade in {"D", "F"}:
            warnings.append({"asset": asset_name, "timeframe": timeframe, "code": "LOW_ARTIFACT_QUALITY_SCORE", "score": score})
        if isinstance(quality, dict) and quality.get("missing_sources"):
            warnings.append({"asset": asset_name, "timeframe": timeframe, "code": "MISSING_SOURCES", "sources": quality.get("missing_sources")})

        timeframe_scores[str(timeframe)] = {
            "quality_score": score,
            "quality_grade": grade,
            "components": {
                "scan_quality": round(scan_quality, 2),
                "scan_status": round(scan_status_score, 2),
                "venue_coverage": round(venue_coverage, 2),
                "ohlcv_coverage": round(ohlcv_coverage_score, 2),
                "ohlcv_status": round(ohlcv_status_score, 2),
                "price_dispersion": round(dispersion_score, 2),
                "orderbook_coverage": round(book_coverage_score, 2),
                "orderbook_status": round(book_status_score, 2),
            },
        }

    asset_score = _average([item["quality_score"] for item in timeframe_scores.values()], 0.0)
    asset_score = round(asset_score, 2)
    return {
        "asset": asset_name or run_summary.get("asset") if isinstance(run_summary, dict) else asset_name,
        "artifact_dir": str(asset_dir),
        "quality_score": asset_score,
        "quality_grade": _grade(asset_score),
        "timeframes": timeframe_scores,
        "warnings": warnings,
    }


def score_artifact_root(artifact_root: str | Path) -> dict[str, Any]:
    root = Path(artifact_root)
    validation = validate_artifact_root(root)
    result: dict[str, Any] = {
        "status": "OK",
        "artifact_root": str(root),
        "mode": validation.get("mode", "unknown"),
        "quality_score": 0.0,
        "quality_grade": "F",
        "assets_checked": 0,
        "asset_scores": {},
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
        summary = _read_json(root / "universe_summary.json") or {}
        asset_results = summary.get("asset_results", {}) if isinstance(summary, dict) else {}
        scores = []
        if isinstance(asset_results, dict):
            for asset, item in sorted(asset_results.items()):
                if not isinstance(item, dict) or item.get("error"):
                    continue
                artifact_dir = item.get("artifact_dir")
                if not isinstance(artifact_dir, str) or not artifact_dir.strip():
                    continue
                asset_score = _score_single_asset(root / artifact_dir, asset)
                result["asset_scores"][asset] = asset_score
                result["warnings"].extend(asset_score["warnings"])
                scores.append(asset_score["quality_score"])
        result["assets_checked"] = len(scores)
        result["quality_score"] = round(_average(scores, 0.0), 2)
    else:
        asset_score = _score_single_asset(root)
        asset_key = asset_score.get("asset") or root.name
        result["asset_scores"][str(asset_key)] = asset_score
        result["warnings"].extend(asset_score["warnings"])
        result["assets_checked"] = 1 if asset_score["timeframes"] else 0
        result["quality_score"] = asset_score["quality_score"]

    result["quality_grade"] = _grade(float(result["quality_score"]))
    if validation.get("status") == "WARN" or result["warnings"]:
        result["status"] = "WARN"
    return result


def write_quality_score(artifact_root: str | Path, output_name: str = "quality_score.json") -> dict[str, Any]:
    root = Path(artifact_root)
    result = score_artifact_root(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / output_name).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result