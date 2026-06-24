from __future__ import annotations

import json
from pathlib import Path

import pytest

from crypto_composite import cli
from crypto_composite.artifact_report import assert_no_forbidden_report_terms, write_static_report


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
        "bars_by_market_type": {
            "spot_usdt": [
                {
                    "asset": asset,
                    "timeframe": "15m",
                    "market_type": "spot_usdt",
                    "timestamp_ms": 1000,
                    "open": 99.0,
                    "high": 101.0,
                    "low": 98.5,
                    "close": 100.0,
                    "volume_base_total": 10.0,
                    "coverage": 1.0,
                    "price_dispersion_pct": 0.03,
                    "data_quality": 0.91,
                },
                {
                    "asset": asset,
                    "timeframe": "15m",
                    "market_type": "spot_usdt",
                    "timestamp_ms": 2000,
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.5,
                    "close": 101.0,
                    "volume_base_total": 12.0,
                    "coverage": 1.0,
                    "price_dispersion_pct": 0.02,
                    "data_quality": 0.93,
                },
            ],
            "perp_usdt": [
                {
                    "asset": asset,
                    "timeframe": "15m",
                    "market_type": "perp_usdt",
                    "timestamp_ms": 2000,
                    "open": 100.0,
                    "high": 101.5,
                    "low": 99.7,
                    "close": 100.8,
                    "volume_base_total": 15.0,
                    "coverage": 1.0,
                    "price_dispersion_pct": 0.03,
                    "data_quality": 0.92,
                }
            ],
        },
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
            "top_bid_wall": {
                "side": "bid",
                "price_mid": 99.5,
                "depth_quote": 1000.0,
                "venue_count": 3,
                "spoof_risk_proxy": 0.05,
                "vacuum_score": 0.1,
            },
            "top_ask_wall": {
                "side": "ask",
                "price_mid": 102.5,
                "depth_quote": 900.0,
                "venue_count": 2,
                "spoof_risk_proxy": 0.15,
                "vacuum_score": 0.2,
            },
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


def test_report_wording_guard_ignores_forbidden_tokens_inside_schema_fields() -> None:
    assert_no_forbidden_report_terms('<span data-field="outputs">outputs</span>')


def test_report_wording_guard_rejects_standalone_tp() -> None:
    with pytest.raises(ValueError, match="FORBIDDEN_REPORT_TERM: TP"):
        assert_no_forbidden_report_terms("<p>TP</p>")


def test_write_static_report_creates_html(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    out_file = tmp_path / "report.html"
    _write_single_asset(artifact_root)

    result = write_static_report(artifact_root, out_file)

    html = out_file.read_text(encoding="utf-8")
    assert result["status"] == "OK"
    assert result["quality_grade"] in {"A", "B"}
    assert "Crypto Composite Artifact Report" in html
    assert "Operational briefing" in html
    assert "DID" in html
    assert "DOING" in html
    assert "NEXT MONITOR" in html
    assert "KEY LEVELS" in html
    assert "RISK CONTEXT" in html
    assert "Recent composite close advanced" in html
    assert "Bid wall" in html
    assert "Ask wall" in html
    assert "Operational context" in html
    assert "OBSERVATION READY" in html
    assert "Operator mode" in html
    assert "Monitor-only public data" in html
    assert "spot_usdt" in html
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
