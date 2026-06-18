from __future__ import annotations

from pathlib import Path

import pytest

from crypto_composite import cli
from crypto_composite.universe import asset_slug, run_universe
from crypto_composite.utils import read_json


def test_asset_slug_normalizes_asset_label() -> None:
    assert asset_slug(" eth/usdt ") == "ETH-USDT"


def test_run_universe_writes_summary_and_per_asset_dirs(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict] = []

    def fake_run_composite(**kwargs) -> dict:
        calls.append(kwargs)
        Path(kwargs["out_dir"]).mkdir(parents=True, exist_ok=True)
        return {
            "summary": {
                "asset": kwargs["asset"],
                "timeframes": kwargs["timeframes"],
                "outputs": {"data_quality": "data_quality.json"},
                "data_quality_by_timeframe": {"15m": {"status": "OK"}},
            }
        }

    monkeypatch.setattr("crypto_composite.universe.run_composite", fake_run_composite)

    summary = run_universe(
        assets=["BTC-USDT", "ETH-USDT"],
        venues=["binance", "okx"],
        market_types=["spot_usdt"],
        timeframes=["15m"],
        limit=10,
        depth=5,
        out_dir=tmp_path,
    )

    assert [call["asset"] for call in calls] == ["BTC-USDT", "ETH-USDT"]
    assert (tmp_path / "BTC-USDT").is_dir()
    assert (tmp_path / "ETH-USDT").is_dir()
    assert summary["asset_count"] == 2
    assert summary["errors"] == []
    assert read_json(tmp_path / "universe_summary.json")["outputs"]["per_asset_artifacts"] == {
        "BTC-USDT": "BTC-USDT",
        "ETH-USDT": "ETH-USDT",
    }


def test_run_universe_rejects_empty_asset_list(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ASSET_UNIVERSE_EMPTY"):
        run_universe(assets=[], out_dir=tmp_path)


def test_cli_universe_parses_assets_and_prints_status(monkeypatch, capsys) -> None:
    calls: list[dict] = []

    def fake_run_universe(**kwargs) -> dict:
        calls.append(kwargs)
        return {"asset_count": len(kwargs["assets"]), "timeframes": kwargs["timeframes"]}

    monkeypatch.setattr(cli, "run_universe", fake_run_universe)
    monkeypatch.setattr(
        "sys.argv",
        [
            "crypto-composite",
            "universe",
            "--assets",
            "BTC-USDT, ETH-USDT",
            "--venues",
            "binance,okx",
            "--market-types",
            "spot_usdt",
            "--timeframes",
            "15m,1h",
            "--limit",
            "20",
            "--depth",
            "10",
            "--out-dir",
            "artifacts-universe",
        ],
    )

    cli.main()

    assert calls[0]["assets"] == ["BTC-USDT", "ETH-USDT"]
    assert calls[0]["timeframes"] == ["15m", "1h"]
    assert capsys.readouterr().out.strip() == "STATUS: OK assets=2 timeframes=15m,1h out_dir=artifacts-universe"
