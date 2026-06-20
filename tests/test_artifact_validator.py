from __future__ import annotations

import json
from pathlib import Path

import pytest

from crypto_composite import cli
from crypto_composite.artifact_validator import validate_artifact_root


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _quality_report(asset: str) -> dict:
    return {
        "asset": asset,
        "venues_requested": ["binance", "okx"],
        "venues_ok": ["binance", "okx"],
        "venues_failed": [],
        "market_types": ["spot_usdt"],
        "timeframe": "15m",
        "missing_sources": [],
        "overall_quality": 0.9,
        "status": "OK",
    }


def _ohlcv_context(asset: str) -> dict:
    return {
        "asset": asset,
        "timeframe": "15m",
        "generated_at_ms": 1000,
        "expected_venues": ["binance", "okx"],
        "bars_by_market_type": {},
        "latest_by_market_type": {},
        "status_by_market_type": {},
        "coverage_by_market_type": {},
        "notes": [],
    }


def _ladder_document(asset: str) -> dict:
    return {
        "spot_usdt": {
            "asset": asset,
            "market_type": "spot_usdt",
            "generated_at_ms": 1000,
            "reference_price": 100.0,
            "bucket_size": 1.0,
            "expected_venues": ["binance", "okx"],
            "venue_count": 2,
            "coverage": 1.0,
            "bid_levels": [],
            "ask_levels": [],
            "top_bid_wall": None,
            "top_ask_wall": None,
            "bid_depth_total": 0.0,
            "ask_depth_total": 0.0,
            "depth_imbalance": 0.0,
            "status": "COMPOSITE_BOOK_OK",
            "notes": [],
        }
    }


def _write_single_asset_artifacts(root: Path, asset: str = "BTC-USDT") -> None:
    quality = _quality_report(asset)
    ohlcv = _ohlcv_context(asset)
    ladder = _ladder_document(asset)
    _write_json(
        root / "run_summary.json",
        {
            "asset": asset,
            "venues": ["binance", "okx"],
            "market_types": ["spot_usdt"],
            "timeframes": ["15m"],
            "outputs": {},
            "data_quality_by_timeframe": {"15m": quality},
            "limitations": [],
        },
    )
    _write_json(root / "data_quality.json", {"15m": quality})
    _write_json(root / "composite_ohlcv.json", {"15m": ohlcv})
    _write_json(root / "composite_orderbook_ladder.json", {"15m": ladder})
    _write_json(root / "composite_ohlcv_15m.json", ohlcv)
    _write_json(root / "composite_orderbook_ladder_15m.json", ladder)


def test_validate_universe_artifacts_ok(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "universe_summary.json",
        {
            "assets": ["BTC-USDT", "ETH-USDT"],
            "venues": ["binance", "okx"],
            "market_types": ["spot_usdt"],
            "timeframes": ["15m"],
            "asset_count": 2,
            "asset_results": {
                "BTC-USDT": {"artifact_dir": "BTC-USDT"},
                "ETH-USDT": {"artifact_dir": "ETH-USDT"},
            },
            "errors": [],
            "outputs": {},
            "limitations": [],
        },
    )
    _write_single_asset_artifacts(tmp_path / "BTC-USDT", "BTC-USDT")
    _write_single_asset_artifacts(tmp_path / "ETH-USDT", "ETH-USDT")

    result = validate_artifact_root(tmp_path)

    assert result["status"] == "OK"
    assert result["mode"] == "universe"
    assert result["assets_checked"] == 2
    assert result["errors"] == []


def test_validate_run_summary_reports_missing_required_fields(tmp_path: Path) -> None:
    _write_single_asset_artifacts(tmp_path)
    summary = json.loads((tmp_path / "run_summary.json").read_text(encoding="utf-8"))
    del summary["limitations"]
    _write_json(tmp_path / "run_summary.json", summary)

    result = validate_artifact_root(tmp_path)

    error = next(error for error in result["errors"] if error["code"] == "RUN_SUMMARY_FIELDS_MISSING")
    assert error["missing_fields"] == ["limitations"]


def test_validate_composite_ohlcv_reports_missing_required_fields(tmp_path: Path) -> None:
    _write_single_asset_artifacts(tmp_path)
    ohlcv = json.loads((tmp_path / "composite_ohlcv_15m.json").read_text(encoding="utf-8"))
    del ohlcv["notes"]
    _write_json(tmp_path / "composite_ohlcv_15m.json", ohlcv)

    result = validate_artifact_root(tmp_path)

    error = next(error for error in result["errors"] if error["code"] == "COMPOSITE_OHLCV_FIELDS_MISSING")
    assert error["missing_fields"] == ["notes"]
    assert error["timeframe"] == "15m"


def test_validate_orderbook_ladder_reports_missing_required_fields(tmp_path: Path) -> None:
    _write_single_asset_artifacts(tmp_path)
    ladder = json.loads((tmp_path / "composite_orderbook_ladder_15m.json").read_text(encoding="utf-8"))
    del ladder["spot_usdt"]["coverage"]
    _write_json(tmp_path / "composite_orderbook_ladder_15m.json", ladder)

    result = validate_artifact_root(tmp_path)

    error = next(
        error for error in result["errors"] if error["code"] == "COMPOSITE_ORDERBOOK_LADDER_FIELDS_MISSING"
    )
    assert error["missing_fields"] == ["coverage"]
    assert error["market_type"] == "spot_usdt"


def test_validate_data_quality_reports_missing_required_fields(tmp_path: Path) -> None:
    _write_single_asset_artifacts(tmp_path)
    quality = json.loads((tmp_path / "data_quality.json").read_text(encoding="utf-8"))
    del quality["15m"]["overall_quality"]
    _write_json(tmp_path / "data_quality.json", quality)

    result = validate_artifact_root(tmp_path)

    error = next(error for error in result["errors"] if error["code"] == "DATA_QUALITY_FIELDS_MISSING")
    assert error["missing_fields"] == ["overall_quality"]
    assert error["timeframe"] == "15m"


def test_validate_data_quality_rejects_non_object_timeframe(tmp_path: Path) -> None:
    _write_single_asset_artifacts(tmp_path)
    _write_json(tmp_path / "data_quality.json", {"15m": []})

    result = validate_artifact_root(tmp_path)

    error = next(error for error in result["errors"] if error["code"] == "DATA_QUALITY_TIMEFRAME_NOT_OBJECT")
    assert error["timeframe"] == "15m"


def test_validate_raw_scan_fields_when_file_is_present(tmp_path: Path) -> None:
    _write_single_asset_artifacts(tmp_path)
    _write_json(
        tmp_path / "raw_scan_15m.json",
        {"data": {"ohlcv": [], "trades": [], "orderbooks": [], "funding": []}},
    )

    result = validate_artifact_root(tmp_path)

    error = next(error for error in result["errors"] if error["code"] == "RAW_SCAN_DATA_FIELDS_MISSING")
    assert error["missing_fields"] == ["open_interest"]


def test_validate_universe_summary_reports_missing_required_fields(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "universe_summary.json",
        {
            "assets": [],
            "venues": [],
            "market_types": [],
            "timeframes": [],
            "asset_count": 0,
            "asset_results": {},
            "errors": [],
            "limitations": [],
        },
    )

    result = validate_artifact_root(tmp_path)

    error = next(error for error in result["errors"] if error["code"] == "UNIVERSE_SUMMARY_FIELDS_MISSING")
    assert error["missing_fields"] == ["outputs"]


def test_validate_single_asset_missing_timeframe_file_reports_error(tmp_path: Path) -> None:
    _write_single_asset_artifacts(tmp_path)
    (tmp_path / "composite_ohlcv_15m.json").unlink()

    result = validate_artifact_root(tmp_path)

    assert result["status"] == "ERROR"
    assert any(error["code"] == "MISSING_JSON_FILE" for error in result["errors"])


def test_validate_artifacts_rejects_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "run_summary.json").write_text("{not-json", encoding="utf-8")

    result = validate_artifact_root(tmp_path)

    assert result["status"] == "ERROR"
    assert result["errors"][0]["code"] == "INVALID_JSON"


def test_cli_validate_artifacts_prints_json(monkeypatch, capsys, tmp_path: Path) -> None:
    _write_single_asset_artifacts(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["crypto-composite", "validate-artifacts", "--artifact-root", str(tmp_path)],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "OK"
    assert payload["mode"] == "single_asset"


def test_cli_validate_artifacts_exits_nonzero_on_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["crypto-composite", "validate-artifacts", "--artifact-root", str(tmp_path / "missing")],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
