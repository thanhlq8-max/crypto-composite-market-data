from __future__ import annotations

from pathlib import Path

from crypto_composite.pipeline import run_composite
from crypto_composite.schemas import DataQualityReport, OHLCVBar, OrderBookSnapshot
from crypto_composite.utils import read_json


def test_run_composite_writes_expected_artifacts(monkeypatch, tmp_path: Path) -> None:
    def fake_scan(asset: str, venues: list[str], market_types: list[str], timeframe: str, limit: int, depth: int = 100) -> dict:
        return {
            "asset": asset,
            "generated_at_ms": 123,
            "phase": "PHASE_1_DATA_FOUNDATION",
            "venues": venues,
            "timeframe": timeframe,
            "market_types": market_types,
            "data": {
                "ohlcv": [
                    OHLCVBar("binance", "spot_usdt", "BTCUSDT", timeframe, 1000, 100, 101, 99, 100, 1, 100, None, 0.90),
                    OHLCVBar("okx", "spot_usdt", "BTC-USDT", timeframe, 1000, 100, 101, 99, 100, 1, 100, None, 0.90),
                ],
                "trades": [],
                "orderbooks": [
                    OrderBookSnapshot("binance", "spot_usdt", "BTCUSDT", 1000, [(100.0, 1.0)], [(101.0, 1.0)], 100.0, 101.0, 100.5, 1.0, 1, 0.90),
                    OrderBookSnapshot("okx", "spot_usdt", "BTC-USDT", 1001, [(100.1, 1.0)], [(101.1, 1.0)], 100.1, 101.1, 100.6, 1.0, 1, 0.90),
                ],
                "funding": [],
                "open_interest": [],
            },
            "errors": [],
            "quality_report": DataQualityReport(
                asset=asset,
                venues_requested=venues,
                venues_ok=venues,
                venues_failed=[],
                market_types=market_types,
                timeframe=timeframe,
                missing_sources=[],
                overall_quality=0.90,
                status="OK",
            ),
        }

    monkeypatch.setattr("crypto_composite.pipeline.scan", fake_scan)

    result = run_composite(
        asset="BTC-USDT",
        venues=["binance", "okx"],
        market_types=["spot_usdt"],
        timeframes=["15m", "1h"],
        limit=10,
        depth=5,
        out_dir=tmp_path,
        bucket_size=1.0,
    )

    expected_files = {
        "raw_scan_15m.json",
        "raw_scan_1h.json",
        "composite_ohlcv_15m.json",
        "composite_ohlcv_1h.json",
        "composite_orderbook_ladder_15m.json",
        "composite_orderbook_ladder_1h.json",
        "composite_ohlcv.json",
        "composite_orderbook_ladder.json",
        "data_quality.json",
        "run_summary.json",
    }
    assert expected_files == {p.name for p in tmp_path.iterdir() if p.is_file()}
    assert result["summary"]["timeframes"] == ["15m", "1h"]

    summary = read_json(tmp_path / "run_summary.json")
    assert summary["outputs"]["raw_scan_by_timeframe"] == ["raw_scan_15m.json", "raw_scan_1h.json"]
    assert summary["limitations"][-1] == "No trading signal, execution instruction, or profitability claim is generated."

    combined_ohlcv = read_json(tmp_path / "composite_ohlcv.json")
    assert sorted(combined_ohlcv) == ["15m", "1h"]
    assert combined_ohlcv["15m"]["status_by_market_type"]["spot_usdt"] == "COMPOSITE_DATA_OK"

    quality = read_json(tmp_path / "data_quality.json")
    assert quality["15m"]["status"] == "OK"
    assert quality["1h"]["venues_ok"] == ["binance", "okx"]
