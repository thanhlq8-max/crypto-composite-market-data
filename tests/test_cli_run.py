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
