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
    _write_json(root / "run_summary.json", {"asset": asset, "timeframes": ["15m"]})
    _write_json(
        root / "data_quality.json",
        {
            "15m": {
                "asset": asset,
                "venues_requested": ["binance", "okx", "bybit"],
                "venues_ok": ["binance", "okx", "bybit"],
                "venues_failed": [],
                "missing_sources": [],
                "overall_quality": quality,
                "status": "OK",
            }
        },
    )
    _write_json(
        root / "composite_ohlcv.json",
        {
            "15m": {
                "coverage_by_market_type": {"spot_usdt": 1.0, "perp_usdt": 1.0},
                "status_by_market_type": {
                    "spot_usdt": "COMPOSITE_DATA_OK",
                    "perp_usdt": "COMPOSITE_DATA_OK",
                },
                "latest_by_market_type": {
                    "spot_usdt": {"price_dispersion_pct": 0.02},
                    "perp_usdt": {"price_dispersion_pct": 0.03},
                },
            }
        },
    )
    _write_json(
        root / "composite_orderbook_ladder.json",
        {
            "15m": {
                "spot_usdt": {"coverage": 1.0, "status": "COMPOSITE_BOOK_OK"},
                "perp_usdt": {"coverage": 1.0, "status": "COMPOSITE_BOOK_OK"},
            }
        },
    )
    _write_json(root / "composite_ohlcv_15m.json", {"asset": asset})
    _write_json(root / "composite_orderbook_ladder_15m.json", {"asset": asset})


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
            "asset_results": {
                "BTC-USDT": {"artifact_dir": "BTC-USDT"},
                "ETH-USDT": {"artifact_dir": "ETH-USDT"},
            },
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