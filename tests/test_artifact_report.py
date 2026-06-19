from __future__ import annotations

import json
from pathlib import Path

import pytest

from crypto_composite import cli
from crypto_composite.artifact_report import write_static_report


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


def test_write_static_report_creates_html(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    out_file = tmp_path / "report.html"
    _write_single_asset(artifact_root)

    result = write_static_report(artifact_root, out_file)

    html = out_file.read_text(encoding="utf-8")
    assert result["status"] == "OK"
    assert result["quality_grade"] in {"A", "B"}
    assert "Crypto Composite Artifact Report" in html
    assert "BTC-USDT" in html
    assert "composite_ohlcv_15m.json" in html
    assert "BUY" not in html.upper()
    assert "SELL" not in html.upper()
    assert "ENTRY" not in html.upper()


def test_cli_report_prints_json(monkeypatch, capsys, tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    out_file = tmp_path / "report.html"
    _write_single_asset(artifact_root)
    monkeypatch.setattr(
        "sys.argv",
        ["crypto-composite", "report", "--artifact-root", str(artifact_root), "--out-file", str(out_file)],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "OK"
    assert payload["report_path"] == str(out_file)
    assert out_file.exists()


def test_cli_report_exits_nonzero_on_error(monkeypatch, tmp_path: Path) -> None:
    out_file = tmp_path / "report.html"
    monkeypatch.setattr(
        "sys.argv",
        ["crypto-composite", "report", "--artifact-root", str(tmp_path / "missing"), "--out-file", str(out_file)],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
    assert out_file.exists()
