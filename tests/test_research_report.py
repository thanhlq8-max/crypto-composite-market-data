from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from crypto_composite import cli
from crypto_composite.research_report import (
    assert_no_forbidden_research_terms,
    build_research_summary,
    write_research_report,
)


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROOT = ROOT / "examples" / "sample_artifacts"


def test_build_research_summary_uses_checked_in_sample_artifacts() -> None:
    summary = build_research_summary(SAMPLE_ROOT)

    assert summary["status"] == "OK"
    assert summary["dataset"]["assets"] == ["BTC-USDT", "ETH-USDT"]
    assert summary["dataset"]["primary_timeframe"] == "15m"
    assert summary["dataset"]["profile_timeframes"] == ["5m", "15m", "1h"]
    assert summary["dataset"]["refresh_seconds"] == 60
    assert summary["dataset"]["market_types"] == ["spot_usdt"]
    assert summary["lfx_alignment"]["status"] == "ADAPTED_MONITOR_ONLY"
    assert summary["lfx_alignment"]["profile"]["primary_timeframe"] == "15m"
    assert any(row["panel"] == "NEXT Scenario" for row in summary["lfx_alignment"]["display_contract"])
    assert any(row["panel"] == "MM Mission" for row in summary["lfx_alignment"]["display_contract"])
    assert len(summary["lfx_mission_control"]) == 48
    assert summary["lfx_mission_control"][0]["panel"] == "MM Mission"
    assert len(summary["market_microstructure_metrics"]) == 6
    assert len(summary["observed_zone_evidence"]) == 6
    assert isinstance(summary["artifacts"], list)
    assert isinstance(summary["artifacts"][0], dict)
    first_row = summary["market_microstructure_metrics"][0]
    assert {
        "asset",
        "timeframe",
        "market_type",
        "price_dispersion_pct",
        "bid_depth_total",
        "ask_depth_total",
        "depth_imbalance",
    }.issubset(first_row)


def test_write_research_report_creates_html_and_summary_json(tmp_path: Path) -> None:
    out_file = tmp_path / "research_report.html"
    summary_file = tmp_path / "research_summary.json"

    result = write_research_report(SAMPLE_ROOT, out_file, summary_file)

    html = out_file.read_text(encoding="utf-8")
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    assert result["status"] == "OK"
    assert result["report_path"] == str(out_file)
    assert result["summary_path"] == str(summary_file)
    assert "Crypto Composite Research Dataset Report" in html
    assert "Executive Summary" in html
    assert "Market microstructure metrics" in html
    assert "LFX-2 alignment contract" in html
    assert "LFX mission-control artifact readout" in html
    assert "Observed zone evidence" in html
    assert "Public demo artifacts" in html
    assert "No trading signal" in html
    assert "BTC-USDT" in html
    assert "spot_usdt" in html
    assert "BUY" not in html.upper()
    assert "SELL" not in html.upper()
    assert "ENTRY" not in html.upper()
    assert isinstance(summary["market_microstructure_metrics"], list)
    assert isinstance(summary["observed_zone_evidence"], list)
    assert isinstance(summary["lfx_mission_control"], list)
    assert isinstance(summary["lfx_alignment"]["display_contract"], list)
    assert isinstance(summary["observed_zone_evidence"][0]["observed_zones"], list)


def test_research_report_wording_guard_rejects_standalone_entry() -> None:
    with pytest.raises(ValueError, match="FORBIDDEN_RESEARCH_TERM: ENTRY"):
        assert_no_forbidden_research_terms("<p>entry</p>")


def test_cli_research_report_prints_json(monkeypatch, capsys, tmp_path: Path) -> None:
    calls: list[tuple[object, object, object]] = []

    def fake_write_research_report(artifact_root: object, out_file: object, summary_file: object) -> dict:
        calls.append((artifact_root, out_file, summary_file))
        return {"status": "OK", "report_path": str(out_file), "summary_path": str(summary_file)}

    monkeypatch.setattr(cli, "write_research_report", fake_write_research_report)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "crypto-composite",
            "research-report",
            "--artifact-root",
            "examples/sample_artifacts",
            "--out-file",
            str(tmp_path / "research_report.html"),
            "--summary-file",
            str(tmp_path / "research_summary.json"),
        ],
    )

    cli.main()

    assert calls == [
        (
            "examples/sample_artifacts",
            str(tmp_path / "research_report.html"),
            str(tmp_path / "research_summary.json"),
        )
    ]
    assert json.loads(capsys.readouterr().out)["status"] == "OK"
