from __future__ import annotations

import json
from pathlib import Path

import pytest

from crypto_composite import cli
from crypto_composite.artifact_quality import score_artifact_root, write_quality_score


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_single_asset(root: Path, asset: str = "BTC-USDT", quality: float = 0.90) -> None:
    quality_report = {
        "asset": asset,
        "venues_requested": ["binance", "okx", "bybit"],
        "venues_ok": ["binance", "okx", "bybit"],
        "venues_failed": [],
        "market_types": ["spot_usdt", "perp_usdt"],
        "timeframe": "15m",
        "missing_sources": [],
        "overall_quality": quality,
        "status": "OK",
    }
    ohlcv_context = {
        "asset": asset,
        "timeframe": "15m",
        "generated_at_ms": 1000,
        "expected_venues": ["binance", "okx", "bybit"],
        "bars_by_market_type": {},
        "coverage_by_market_type": {"spot_usdt": 1.0, "perp_usdt": 1.0},
        "status_by_market_type": {
            "spot_usdt": "COMPOSITE_DATA_OK",
            "perp_usdt": "COMPOSITE_DATA_OK",
        },
        "latest_by_market_type": {
            "spot_usdt": {"price_dispersion_pct": 0.02},
            "perp_usdt": {"price_dispersion_pct": 0.03},
        },
        "notes": [],
    }

    def ladder(market_type: str) -> dict:
        return {
            "asset": asset,
            "market_type": market_type,
            "generated_at_ms": 1000,
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


def test_score_single_asset_ok(tmp_path: Path) -> None:
    _write_single_asset(tmp_path)

    result = score_artifact_root(tmp_path)

    assert result["status"] == "OK"
    assert result["quality_grade"] in {"A", "B"}
    assert result["quality_score"] >= 85.0
    assert result["assets_checked"] == 1
    assert "trading signal" in result["boundaries"][0]


def test_score_universe_averages_assets(tmp_path: Path) -> None:
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
    _write_single_asset(tmp_path / "BTC-USDT", "BTC-USDT", quality=0.95)
    _write_single_asset(tmp_path / "ETH-USDT", "ETH-USDT", quality=0.75)

    result = score_artifact_root(tmp_path)

    assert result["status"] == "OK"
    assert result["mode"] == "universe"
    assert result["assets_checked"] == 2
    assert set(result["asset_scores"]) == {"BTC-USDT", "ETH-USDT"}


def test_score_artifacts_returns_error_when_validation_fails(tmp_path: Path) -> None:
    result = score_artifact_root(tmp_path / "missing")

    assert result["status"] == "ERROR"
    assert result["quality_grade"] == "F"
    assert result["errors"]


def test_write_quality_score_writes_json(tmp_path: Path) -> None:
    _write_single_asset(tmp_path)

    result = write_quality_score(tmp_path)

    written = json.loads((tmp_path / "quality_score.json").read_text(encoding="utf-8"))
    assert written["quality_score"] == result["quality_score"]


def test_cli_score_artifacts_prints_json(monkeypatch, capsys, tmp_path: Path) -> None:
    _write_single_asset(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["crypto-composite", "score-artifacts", "--artifact-root", str(tmp_path), "--write"],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "OK"
    assert (tmp_path / "quality_score.json").exists()


def test_cli_score_artifacts_exits_nonzero_on_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["crypto-composite", "score-artifacts", "--artifact-root", str(tmp_path / "missing")],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
