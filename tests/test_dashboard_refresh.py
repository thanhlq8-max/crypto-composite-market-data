from __future__ import annotations

import json
from pathlib import Path

import pytest

from crypto_composite import dashboard_refresh


def test_run_dashboard_refresh_single_cycle_writes_profile_and_dashboard(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict] = []

    def fake_run_universe(**kwargs) -> dict:
        calls.append(kwargs)
        return {
            "asset_count": len(kwargs["assets"]),
            "timeframes": kwargs["timeframes"],
            "errors": [],
        }

    def fake_validate_artifact_root(root: object) -> dict:
        return {"status": "OK", "errors": [], "warnings": []}

    def fake_write_quality_score(root: object) -> dict:
        return {"status": "OK", "quality_score": 95.0, "quality_grade": "A", "errors": [], "warnings": []}

    def fake_write_dashboard_export(**kwargs) -> dict:
        return {"status": "OK", "dashboard_path": str(kwargs["out_file"]), "errors": [], "warnings": []}

    monkeypatch.setattr(dashboard_refresh, "run_universe", fake_run_universe)
    monkeypatch.setattr(dashboard_refresh, "validate_artifact_root", fake_validate_artifact_root)
    monkeypatch.setattr(dashboard_refresh, "write_quality_score", fake_write_quality_score)
    monkeypatch.setattr(dashboard_refresh, "write_dashboard_export", fake_write_dashboard_export)

    out_dir = tmp_path / "artifacts-live"
    dashboard_file = out_dir / "dashboard.html"

    result = dashboard_refresh.run_dashboard_refresh(
        assets=["BTC-USDT", "ETH-USDT"],
        venues=["binance", "okx", "bybit"],
        market_types=["spot_usdt", "perp_usdt"],
        timeframes=["5m", "15m", "1h"],
        primary_timeframe="15m",
        refresh_seconds=60,
        limit=120,
        depth=100,
        bucket_size=1.0,
        out_dir=out_dir,
        dashboard_file=dashboard_file,
        artifact_base_url=".",
        max_cycles=1,
    )

    profile = json.loads((out_dir / "dashboard_profile.json").read_text(encoding="utf-8"))
    assert result["status"] == "OK"
    assert result["cycles_completed"] == 1
    assert result["last_cycle"]["quality_score"] == 95.0
    assert calls == [
        {
            "assets": ["BTC-USDT", "ETH-USDT"],
            "venues": ["binance", "okx", "bybit"],
            "market_types": ["spot_usdt", "perp_usdt"],
            "timeframes": ["5m", "15m", "1h"],
            "limit": 120,
            "depth": 100,
            "out_dir": out_dir,
            "bucket_size": 1.0,
        }
    ]
    assert profile["primary_timeframe"] == "15m"
    assert profile["timeframes"] == ["5m", "15m", "1h"]
    assert profile["refresh_seconds"] == 60


def test_run_dashboard_refresh_rejects_primary_timeframe_outside_profile(tmp_path: Path) -> None:
    with pytest.raises(dashboard_refresh.DashboardRefreshError, match="PRIMARY_TIMEFRAME_NOT_IN_TIMEFRAMES"):
        dashboard_refresh.run_dashboard_refresh(
            assets=["BTC-USDT"],
            venues=["binance"],
            market_types=["spot_usdt"],
            timeframes=["5m", "1h"],
            primary_timeframe="15m",
            refresh_seconds=60,
            limit=10,
            depth=10,
            bucket_size=1.0,
            out_dir=tmp_path,
            dashboard_file=tmp_path / "dashboard.html",
            artifact_base_url=".",
            max_cycles=1,
        )
