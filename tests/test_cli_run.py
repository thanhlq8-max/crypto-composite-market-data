from __future__ import annotations

import sys

from crypto_composite import cli


def test_cli_run_parses_arguments_and_prints_status(monkeypatch, capsys) -> None:
    calls: list[dict] = []

    def fake_run_composite(**kwargs) -> dict:
        calls.append(kwargs)
        return {"summary": {"asset": kwargs["asset"], "timeframes": kwargs["timeframes"]}}

    monkeypatch.setattr(cli, "run_composite", fake_run_composite)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "crypto-composite",
            "run",
            "--asset",
            "ETH-USDT",
            "--venues",
            "binance, okx",
            "--market-types",
            "spot_usdt",
            "--timeframes",
            "15m, 1h",
            "--limit",
            "50",
            "--depth",
            "25",
            "--out-dir",
            "tmp-artifacts",
            "--bucket-size",
            "5",
        ],
    )

    cli.main()

    assert calls == [
        {
            "asset": "ETH-USDT",
            "venues": ["binance", "okx"],
            "market_types": ["spot_usdt"],
            "timeframes": ["15m", "1h"],
            "limit": 50,
            "depth": 25,
            "out_dir": "tmp-artifacts",
            "bucket_size": 5.0,
        }
    ]
    assert capsys.readouterr().out.strip() == "STATUS: OK asset=ETH-USDT timeframes=15m,1h out_dir=tmp-artifacts"


def test_cli_dashboard_invokes_server(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_serve_dashboard(**kwargs) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(cli, "serve_dashboard", fake_serve_dashboard)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "crypto-composite",
            "dashboard",
            "--artifact-root",
            "examples/sample_artifacts",
            "--host",
            "127.0.0.1",
            "--port",
            "18080",
        ],
    )

    cli.main()

    assert calls == [
        {
            "artifact_root": "examples/sample_artifacts",
            "host": "127.0.0.1",
            "port": 18080,
        }
    ]
