from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from crypto_composite.artifact_quality import score_artifact_root
from crypto_composite.artifact_validator import validate_artifact_root
from crypto_composite.dashboard_analytics import build_dashboard_snapshot


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROOT = ROOT / "examples" / "sample_artifacts"
EXAMPLE_PATH = ROOT / "examples" / "inspect_quality.py"


def _load_example_module():
    spec = importlib.util.spec_from_file_location("inspect_quality_example", EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_in_sample_artifacts_validate_and_score() -> None:
    validation = validate_artifact_root(SAMPLE_ROOT)
    quality = score_artifact_root(SAMPLE_ROOT)

    assert validation["status"] == "OK"
    assert validation["mode"] == "universe"
    assert validation["assets_checked"] == 2
    assert validation["errors"] == []
    assert quality["status"] == "OK"
    assert quality["assets_checked"] == 2
    assert sorted(quality["asset_scores"]) == ["BTC-USDT", "ETH-USDT"]


def test_checked_in_sample_dashboard_uses_locked_mtf_profile() -> None:
    snapshot = build_dashboard_snapshot(SAMPLE_ROOT)

    assert snapshot["profile"]["primary_timeframe"] == "15m"
    assert snapshot["profile"]["timeframes"] == ["5m", "15m", "1h"]
    assert snapshot["profile"]["refresh_seconds"] == 60
    assert snapshot["lfx_alignment"]["status"] == "ADAPTED_MONITOR_ONLY"
    assert snapshot["lfx_alignment"]["profile"]["primary_timeframe"] == "15m"
    assert any(row["panel"] == "MM Mission" for row in snapshot["lfx_alignment"]["display_contract"])
    assert any(row["panel"] == "KEY Zones" for row in snapshot["lfx_alignment"]["display_contract"])
    assert [asset["asset"] for asset in snapshot["assets"]] == ["BTC-USDT", "ETH-USDT"]
    assert [
        [timeframe["timeframe"] for timeframe in asset["timeframes"]]
        for asset in snapshot["assets"]
    ] == [["15m", "5m", "1h"], ["15m", "5m", "1h"]]
    for asset in snapshot["assets"]:
        mtf_map = asset["mtf_zone_map"]
        assert mtf_map["primary_timeframe"] == "15m"
        assert mtf_map["timeframe_count"] == 3
        assert {row["timeframe"] for row in mtf_map["rows"]} == {"5m", "15m", "1h"}
        assert any(row["timeframe"] == "15m" and row["is_primary"] for row in mtf_map["rows"])
        assert all("nearest_bid" in row and "nearest_ask" in row for row in mtf_map["rows"])
        for timeframe in asset["timeframes"]:
            for market in timeframe["markets"]:
                assert market["zone_readout"]["title"].endswith("zones corroborated")
                assert market["zone_readout"]["evidence_mix"]["total_zones"] == len(market["observed_zones"])
                assert len(market["lfx_mission_control"]["rows"]) == 8
                assert market["lfx_mission_control"]["rows"][0]["panel"] == "MM Mission"
                assert "future-reaction" in market["zone_readout"]["limitation"]


def test_inspect_quality_example_emits_compact_json(capsys) -> None:
    module = _load_example_module()

    exit_code = module.main(["--artifact-root", str(SAMPLE_ROOT)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "OK"
    assert payload["mode"] == "universe"
    assert payload["assets_checked"] == 2
    assert [item["asset"] for item in payload["assets"]] == ["BTC-USDT", "ETH-USDT"]
    assert payload["validation_errors"] == []
