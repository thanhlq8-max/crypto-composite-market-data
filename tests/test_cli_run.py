from __future__ import annotations

import json
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


def test_cli_dashboard_export_invokes_writer(monkeypatch, capsys) -> None:
    calls: list[dict] = []

    def fake_write_dashboard_export(**kwargs) -> dict:
        calls.append(kwargs)
        return {"status": "OK", "dashboard_path": "site/index.html"}

    monkeypatch.setattr(cli, "write_dashboard_export", fake_write_dashboard_export)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "crypto-composite",
            "dashboard-export",
            "--artifact-root",
            "examples/sample_artifacts",
            "--out-file",
            "site/index.html",
            "--artifact-base-url",
            "artifacts",
        ],
    )

    cli.main()

    assert calls == [
        {
            "artifact_root": "examples/sample_artifacts",
            "out_file": "site/index.html",
            "artifact_base_url": "artifacts",
        }
    ]
    assert json.loads(capsys.readouterr().out)["status"] == "OK"


def test_cli_dashboard_profile_writes_metadata(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "crypto-composite",
            "dashboard-profile",
            "--artifact-root",
            str(tmp_path),
            "--primary-timeframe",
            "15m",
            "--timeframes",
            "5m,15m,1h",
            "--refresh-seconds",
            "60",
        ],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "OK"
    assert payload["profile"]["primary_timeframe"] == "15m"
    assert payload["profile"]["timeframes"] == ["5m", "15m", "1h"]
    assert payload["profile"]["refresh_seconds"] == 60


def test_cli_dashboard_refresh_requires_explicit_profile_inputs(monkeypatch, capsys) -> None:
    calls: list[dict] = []

    def fake_run_dashboard_refresh(**kwargs) -> dict:
        calls.append(kwargs)
        return {"status": "OK", "cycles_completed": 1}

    monkeypatch.setattr(cli, "run_dashboard_refresh", fake_run_dashboard_refresh)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "crypto-composite",
            "dashboard-refresh",
            "--assets",
            "BTC-USDT,ETH-USDT",
            "--venues",
            "binance,okx,bybit",
            "--market-types",
            "spot_usdt,perp_usdt",
            "--timeframes",
            "5m,15m,1h",
            "--primary-timeframe",
            "15m",
            "--refresh-seconds",
            "60",
            "--limit",
            "120",
            "--depth",
            "100",
            "--bucket-size",
            "1",
            "--out-dir",
            "artifacts-live",
            "--dashboard-file",
            "artifacts-live/dashboard.html",
            "--artifact-base-url",
            ".",
            "--max-cycles",
            "1",
        ],
    )

    cli.main()

    assert calls[0]["assets"] == ["BTC-USDT", "ETH-USDT"]
    assert calls[0]["venues"] == ["binance", "okx", "bybit"]
    assert calls[0]["market_types"] == ["spot_usdt", "perp_usdt"]
    assert calls[0]["timeframes"] == ["5m", "15m", "1h"]
    assert calls[0]["primary_timeframe"] == "15m"
    assert calls[0]["refresh_seconds"] == 60
    assert calls[0]["limit"] == 120
    assert calls[0]["depth"] == 100
    assert calls[0]["bucket_size"] == 1.0
    assert calls[0]["artifact_base_url"] == "."
    assert calls[0]["max_cycles"] == 1
    assert callable(calls[0]["on_cycle"])
    assert json.loads(capsys.readouterr().out)["status"] == "OK"


def test_cli_sample_report_invokes_workflow(monkeypatch, capsys) -> None:
    calls: list[dict] = []

    def fake_run_sample_report(**kwargs) -> dict:
        calls.append(kwargs)
        return {"status": "OK", "report_path": "sample-report/artifact_report.html"}

    monkeypatch.setattr(cli, "run_sample_report", fake_run_sample_report)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "crypto-composite",
            "sample-report",
            "--artifact-root",
            "examples/sample_artifacts",
            "--out-dir",
            "sample-report",
            "--artifact-base-url",
            "artifacts",
        ],
    )

    cli.main()

    assert calls == [
        {
            "artifact_root": "examples/sample_artifacts",
            "out_dir": "sample-report",
            "artifact_base_url": "artifacts",
        }
    ]
    assert json.loads(capsys.readouterr().out)["status"] == "OK"
