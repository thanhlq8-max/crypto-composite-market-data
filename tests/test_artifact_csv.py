from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from crypto_composite import cli
from crypto_composite.artifact_csv import write_composite_ohlcv_csv


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _bar(asset: str, market_type: str, timestamp_ms: int, close: float) -> dict:
    return {
        "asset": asset,
        "timeframe": "15m",
        "market_type": market_type,
        "timestamp_ms": timestamp_ms,
        "open": close - 1.0,
        "high": close + 1.0,
        "low": close - 2.0,
        "close": close,
        "median_close": close,
        "vwap_close": close,
        "volume_base_total": 10.0,
        "volume_quote_total": close * 10.0,
        "venue_count": 3,
        "venue_weights": {"binance": 0.34, "bybit": 0.33, "okx": 0.33},
        "coverage": 1.0,
        "price_dispersion_pct": 0.04,
        "data_quality": 0.95,
    }


def _write_single_asset(root: Path, asset: str = "BTC-USDT") -> None:
    quality_report = {
        "asset": asset,
        "venues_requested": ["binance", "okx", "bybit"],
        "venues_ok": ["binance", "okx", "bybit"],
        "venues_failed": [],
        "market_types": ["spot_usdt", "perp_usdt"],
        "timeframe": "15m",
        "missing_sources": [],
        "overall_quality": 0.95,
        "status": "OK",
    }
    ohlcv_context = {
        "asset": asset,
        "timeframe": "15m",
        "generated_at_ms": 1700000000000,
        "expected_venues": ["binance", "okx", "bybit"],
        "bars_by_market_type": {
            "spot_usdt": [_bar(asset, "spot_usdt", 1699999100000, 100.7)],
            "perp_usdt": [_bar(asset, "perp_usdt", 1699999100000, 100.9)],
        },
        "latest_by_market_type": {
            "spot_usdt": {"price_dispersion_pct": 0.04},
            "perp_usdt": {"price_dispersion_pct": 0.05},
        },
        "status_by_market_type": {
            "spot_usdt": "COMPOSITE_DATA_OK",
            "perp_usdt": "COMPOSITE_DATA_OK",
        },
        "coverage_by_market_type": {"spot_usdt": 1.0, "perp_usdt": 1.0},
        "notes": [],
    }

    def ladder(market_type: str) -> dict:
        return {
            "asset": asset,
            "market_type": market_type,
            "generated_at_ms": 1700000000000,
            "reference_price": 100.0,
            "bucket_size": 1.0,
            "expected_venues": ["binance", "okx", "bybit"],
            "venue_count": 3,
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

    ladder_document = {"spot_usdt": ladder("spot_usdt"), "perp_usdt": ladder("perp_usdt")}
    _write_json(
        root / "run_summary.json",
        {
            "asset": asset,
            "venues": ["binance", "okx", "bybit"],
            "market_types": ["spot_usdt", "perp_usdt"],
            "timeframes": ["15m"],
            "outputs": {},
            "data_quality_by_timeframe": {"15m": quality_report},
            "limitations": [],
        },
    )
    _write_json(root / "data_quality.json", {"15m": quality_report})
    _write_json(root / "composite_ohlcv.json", {"15m": ohlcv_context})
    _write_json(root / "composite_orderbook_ladder.json", {"15m": ladder_document})
    _write_json(root / "composite_ohlcv_15m.json", ohlcv_context)
    _write_json(root / "composite_orderbook_ladder_15m.json", ladder_document)


def test_export_single_asset_composite_ohlcv_csv(tmp_path: Path) -> None:
    _write_single_asset(tmp_path)
    out_file = tmp_path / "composite_ohlcv.csv"

    result = write_composite_ohlcv_csv(tmp_path, out_file)

    rows = list(csv.DictReader(out_file.open(encoding="utf-8")))
    assert result["status"] == "OK"
    assert result["row_count"] == 2
    assert {row["market_type"] for row in rows} == {"spot_usdt", "perp_usdt"}
    assert rows[0]["asset"] == "BTC-USDT"
    assert "venue_weights_json" in rows[0]
    assert "trading signal" in result["boundaries"][0]


def test_export_universe_composite_ohlcv_csv(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "universe_summary.json",
        {
            "assets": ["BTC-USDT", "ETH-USDT"],
            "venues": ["binance", "okx", "bybit"],
            "market_types": ["spot_usdt", "perp_usdt"],
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
    _write_single_asset(tmp_path / "BTC-USDT", "BTC-USDT")
    _write_single_asset(tmp_path / "ETH-USDT", "ETH-USDT")
    out_file = tmp_path / "ohlcv.csv"

    result = write_composite_ohlcv_csv(tmp_path, out_file)

    rows = list(csv.DictReader(out_file.open(encoding="utf-8")))
    assert result["status"] == "OK"
    assert result["assets_checked"] == 2
    assert result["row_count"] == 4
    assert {row["asset"] for row in rows} == {"BTC-USDT", "ETH-USDT"}


def test_export_csv_returns_error_when_validation_fails(tmp_path: Path) -> None:
    result = write_composite_ohlcv_csv(tmp_path / "missing", tmp_path / "out.csv")

    assert result["status"] == "ERROR"
    assert result["errors"]
    assert not (tmp_path / "out.csv").exists()


def test_cli_export_ohlcv_csv_prints_json(monkeypatch, capsys, tmp_path: Path) -> None:
    _write_single_asset(tmp_path)
    out_file = tmp_path / "flat.csv"
    monkeypatch.setattr(
        "sys.argv",
        ["crypto-composite", "export-ohlcv-csv", "--artifact-root", str(tmp_path), "--out-file", str(out_file)],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "OK"
    assert payload["row_count"] == 2
    assert out_file.exists()


def test_cli_export_ohlcv_csv_exits_nonzero_on_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "crypto-composite",
            "export-ohlcv-csv",
            "--artifact-root",
            str(tmp_path / "missing"),
            "--out-file",
            str(tmp_path / "flat.csv"),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1