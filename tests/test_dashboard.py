from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest

from crypto_composite.dashboard import (
    DashboardBindError,
    DashboardInputError,
    build_artifact_index,
    load_json_artifact,
    serve_dashboard,
    write_dashboard_export,
    _safe_json_path,
    make_dashboard_handler,
)
from crypto_composite.dashboard_analytics import build_dashboard_snapshot
from crypto_composite.dashboard_frontend import render_dashboard_html
from crypto_composite.dashboard_profile import write_dashboard_profile


def test_build_artifact_index_lists_json_files(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "run_summary.json").write_text('{"status":"OK"}', encoding="utf-8")
    (tmp_path / "nested" / "data_quality.json").write_text('{"status":"OK"}', encoding="utf-8")
    (tmp_path / "README.md").write_text("ignore", encoding="utf-8")

    index = build_artifact_index(tmp_path)

    assert index["artifact_count"] == 2
    assert index["well_known"]["run_summary.json"] is True
    assert index["artifacts"] == [
        {
            "path": "nested/data_quality.json",
            "size_bytes": (tmp_path / "nested" / "data_quality.json").stat().st_size,
        },
        {
            "path": "run_summary.json",
            "size_bytes": (tmp_path / "run_summary.json").stat().st_size,
        },
    ]


def test_render_dashboard_html_reads_object_artifact_contract() -> None:
    html = render_dashboard_html()

    assert "Observed Market Structure" in html
    assert "Dashboard V3 / practical monitoring brief" in html
    assert 'id="confidence-title"' in html
    assert "distance_to_reference_pct" in html
    assert 'getJson("/api/dashboard-snapshot")' in html
    assert 'getJson("/api/artifacts")' in html
    assert "item.path" in html
    assert "item.size_bytes" in html
    assert 'id="profile-note"' in html
    assert 'id="zone-readout"' in html
    assert "Observed zone readout" in html
    assert 'id="mtf-zone-map"' in html
    assert "Multi-timeframe zone map" in html
    assert "\u00c2" not in html
    assert ">Buy<" not in html
    assert ">Sell<" not in html


def test_dashboard_http_root_serves_html_and_api_serves_objects(tmp_path: Path) -> None:
    artifact = tmp_path / "data_quality.json"
    artifact.write_text('{"15m":{"status":"OK"}}', encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_dashboard_handler(tmp_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        with urlopen(f"http://{host}:{port}/", timeout=5) as response:
            html = response.read().decode("utf-8")
            assert response.status == 200
            assert response.headers["Content-Type"] == "text/html; charset=utf-8"
            assert "Observed Market Structure" in html

        with urlopen(f"http://{host}:{port}/api/artifacts", timeout=5) as response:
            payload = json.loads(response.read())
            assert response.status == 200
            assert payload["artifacts"] == [{"path": "data_quality.json", "size_bytes": artifact.stat().st_size}]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_load_json_artifact_reads_payload(tmp_path: Path) -> None:
    artifact = tmp_path / "data_quality.json"
    artifact.write_text(json.dumps({"status": "OK"}), encoding="utf-8")

    assert load_json_artifact(artifact) == {"status": "OK"}


def test_dashboard_snapshot_builds_observed_zones_and_dislocation(tmp_path: Path) -> None:
    bars = {
        "asset": "BTC-USDT",
        "timeframe": "15m",
        "bars_by_market_type": {
            "spot_usdt": [
                {"timestamp_ms": 1000, "close": 100.0, "coverage": 1.0, "price_dispersion_pct": 0.02},
                {"timestamp_ms": 2000, "close": 101.0, "coverage": 1.0, "price_dispersion_pct": 0.03},
            ],
            "perp_usdt": [{"timestamp_ms": 2000, "close": 101.5, "coverage": 1.0, "price_dispersion_pct": 0.04}],
        },
        "latest_by_market_type": {
            "spot_usdt": {"timestamp_ms": 2000, "close": 101.0, "coverage": 1.0, "price_dispersion_pct": 0.03},
            "perp_usdt": {"timestamp_ms": 2000, "close": 101.5, "coverage": 1.0, "price_dispersion_pct": 0.04},
        },
        "status_by_market_type": {"spot_usdt": "COMPOSITE_DATA_OK", "perp_usdt": "COMPOSITE_DATA_OK"},
    }
    bid_wall = {
        "side": "bid", "price_low": 99.0, "price_high": 100.0, "price_mid": 99.5,
        "depth_quote": 1000.0, "venue_count": 3,
        "venue_depth_quote": {"binance": 340.0, "okx": 330.0, "bybit": 330.0},
        "hhi": 0.3334, "persistence": 0.67, "spoof_risk_proxy": 0.05, "vacuum_score": 0.0,
    }
    bid_vacuum = {
        "side": "bid", "price_low": 98.0, "price_high": 99.0, "price_mid": 98.5,
        "depth_quote": 100.0, "venue_count": 1, "venue_depth_quote": {"binance": 100.0},
        "hhi": 1.0, "persistence": 0.35, "spoof_risk_proxy": 0.7, "vacuum_score": 0.9,
    }
    ask_wall = {
        "side": "ask", "price_low": 102.0, "price_high": 103.0, "price_mid": 102.5,
        "depth_quote": 900.0, "venue_count": 2,
        "venue_depth_quote": {"binance": 600.0, "okx": 300.0},
        "hhi": 0.5556, "persistence": 0.61, "spoof_risk_proxy": 0.2, "vacuum_score": 0.1,
    }
    ladder = {
        "asset": "BTC-USDT", "market_type": "spot_usdt", "generated_at_ms": 2000,
        "reference_price": 101.0, "coverage": 1.0, "venue_count": 3,
        "bid_depth_total": 1100.0, "ask_depth_total": 900.0, "depth_imbalance": 0.1,
        "status": "COMPOSITE_BOOK_OK",
        "bid_levels": [bid_wall, bid_vacuum], "ask_levels": [ask_wall],
        "top_bid_wall": bid_wall, "top_ask_wall": ask_wall,
    }
    (tmp_path / "composite_ohlcv.json").write_text(json.dumps({"15m": bars}), encoding="utf-8")
    (tmp_path / "composite_orderbook_ladder.json").write_text(
        json.dumps({"15m": {"spot_usdt": ladder}}), encoding="utf-8"
    )
    (tmp_path / "data_quality.json").write_text(
        json.dumps({"15m": {"status": "OK", "note": "Reviewed fixture; not live data."}}),
        encoding="utf-8",
    )
    (tmp_path / "run_summary.json").write_text(json.dumps({"asset": "BTC-USDT"}), encoding="utf-8")

    snapshot = build_dashboard_snapshot(tmp_path)
    asset = snapshot["assets"][0]
    timeframe = asset["timeframes"][0]
    market = next(item for item in timeframe["markets"] if item["market_type"] == "spot_usdt")

    assert market["observed_zones"][0]["kind"] == "BID_LIQUIDITY_CONCENTRATION"
    assert market["observed_zones"][0]["evidence_grade"] == "CORROBORATED"
    assert market["observed_zones"][0]["reference_relation"] == "BELOW_REFERENCE"
    assert market["observed_zones"][0]["distance_to_reference_pct"] == pytest.approx(0.990099)
    assert market["observed_zones"][1]["kind"] == "BID_PUBLIC_DEPTH_VACUUM"
    assert market["observed_zones"][1]["evidence_grade"] == "LIMITED"
    assert market["observed_zones"][2]["evidence_grade"] == "CONCENTRATED"
    assert market["observed_zones"][2]["reference_relation"] == "ABOVE_REFERENCE"
    assert market["observed_zones"][2]["distance_to_reference_pct"] == pytest.approx(0.990099)
    assert market["monitoring_brief"]["past"] == {
        "timeframe": "15m",
        "bar_count": 2,
        "close_change_pct": 1.0,
    }
    assert market["monitoring_brief"]["now"]["book"] == {
        "status": "COMPOSITE_BOOK_OK",
        "reference_price": 101.0,
        "coverage": 1.0,
        "venue_count": 3,
        "bid_depth_total": 1100.0,
        "ask_depth_total": 900.0,
        "depth_imbalance": 0.1,
    }
    assert market["monitoring_brief"]["now"]["nearest_bid_concentration"]["price_low"] == 99.0
    assert market["monitoring_brief"]["now"]["nearest_ask_concentration"]["price_low"] == 102.0
    assert market["monitoring_brief"]["next_evidence_check"]["kind"] == "REFRESH_ZONE_EVIDENCE"
    assert market["monitoring_brief"]["confidence_risk"]["evidence_grade_counts"] == {
        "CORROBORATED": 1,
        "CONCENTRATED": 1,
        "LIMITED": 1,
    }
    assert market["zone_readout"]["title"] == "1/3 zones corroborated"
    assert "Nearest bid concentration 0.990% below reference" in market["zone_readout"]["detail"]
    assert "Nearest ask concentration 0.990% above reference" in market["zone_readout"]["detail"]
    assert market["zone_readout"]["evidence_mix"] == {
        "total_zones": 3,
        "corroborated": 1,
        "concentrated": 1,
        "limited": 1,
    }
    assert market["zone_readout"]["next_check"] == (
        "Compare the nearest concentration ranges, contributing venues, majority share, and depth quote."
    )
    assert timeframe["source_note"] == "Reviewed fixture; not live data."
    assert timeframe["spot_perp_dislocation"]["basis_pct"] == pytest.approx(0.4950495)
    assert asset["mtf_zone_map"]["primary_timeframe"] is None
    assert asset["mtf_zone_map"]["timeframe_count"] == 1
    spot_row = next(row for row in asset["mtf_zone_map"]["rows"] if row["market_type"] == "spot_usdt")
    assert spot_row["timeframe"] == "15m"
    assert spot_row["corroborated"] == 1
    assert spot_row["nearest_bid"]["summary"] == (
        "0.990% below reference / CORROBORATED"
    )
    assert spot_row["nearest_ask"]["summary"] == (
        "0.990% above reference / CONCENTRATED"
    )
    assert snapshot["mode"] == "OBSERVED_PUBLIC_DATA"


def test_dashboard_snapshot_uses_profile_primary_timeframe_order(tmp_path: Path) -> None:
    contexts = {
        timeframe: {
            "asset": "BTC-USDT",
            "timeframe": timeframe,
            "bars_by_market_type": {"spot_usdt": []},
            "latest_by_market_type": {},
        }
        for timeframe in ["5m", "15m", "1h"]
    }
    (tmp_path / "composite_ohlcv.json").write_text(json.dumps(contexts), encoding="utf-8")
    (tmp_path / "data_quality.json").write_text(
        json.dumps({timeframe: {"status": "OK"} for timeframe in contexts}),
        encoding="utf-8",
    )
    (tmp_path / "run_summary.json").write_text(
        json.dumps({"asset": "BTC-USDT", "timeframes": ["5m", "15m", "1h"]}),
        encoding="utf-8",
    )
    write_dashboard_profile(
        tmp_path,
        primary_timeframe="15m",
        timeframes=["5m", "15m", "1h"],
        refresh_seconds=60,
    )

    snapshot = build_dashboard_snapshot(tmp_path)

    assert snapshot["profile"]["primary_timeframe"] == "15m"
    assert snapshot["profile"]["refresh_seconds"] == 60
    asset = snapshot["assets"][0]
    assert [item["timeframe"] for item in asset["timeframes"]] == ["15m", "5m", "1h"]
    assert asset["mtf_zone_map"]["primary_timeframe"] == "15m"
    assert [item["timeframe"] for item in asset["mtf_zone_map"]["rows"]] == ["15m", "5m", "1h"]
    assert [item["is_primary"] for item in asset["mtf_zone_map"]["rows"]] == [True, False, False]


def test_dashboard_snapshot_endpoint_returns_object(tmp_path: Path) -> None:
    (tmp_path / "composite_ohlcv.json").write_text(
        json.dumps(
            {
                "15m": {
                    "asset": "ETH-USDT",
                    "bars_by_market_type": {"spot_usdt": []},
                    "latest_by_market_type": {},
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "run_summary.json").write_text(json.dumps({"asset": "ETH-USDT"}), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_dashboard_handler(tmp_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with urlopen(f"http://{host}:{port}/api/dashboard-snapshot", timeout=5) as response:
            payload = json.loads(response.read())
            assert response.status == 200
            assert payload["mode"] == "OBSERVED_PUBLIC_DATA"
            assert payload["assets"][0]["asset"] == "ETH-USDT"
            market = payload["assets"][0]["timeframes"][0]["markets"][0]
            assert market["monitoring_brief"]["next_evidence_check"]["kind"] == "GENERATE_BOOK_CONTEXT"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_dashboard_snapshot_prioritizes_partial_ohlcv_warning(tmp_path: Path) -> None:
    (tmp_path / "composite_ohlcv.json").write_text(
        json.dumps(
            {
                "15m": {
                    "asset": "BTC-USDT",
                    "bars_by_market_type": {"spot_usdt": [{"timestamp_ms": 1000, "close": 100.0}]},
                    "latest_by_market_type": {"spot_usdt": {"timestamp_ms": 1000, "close": 100.0}},
                    "status_by_market_type": {"spot_usdt": "COMPOSITE_DATA_PARTIAL"},
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "run_summary.json").write_text(json.dumps({"asset": "BTC-USDT"}), encoding="utf-8")

    snapshot = build_dashboard_snapshot(tmp_path)
    market = snapshot["assets"][0]["timeframes"][0]["markets"][0]

    assert market["monitoring_brief"]["next_evidence_check"]["kind"] == "RESTORE_OHLCV_COVERAGE"


def test_write_dashboard_export_embeds_snapshot_and_safe_index(tmp_path: Path) -> None:
    (tmp_path / "composite_ohlcv.json").write_text(
        json.dumps(
            {
                "15m": {
                    "asset": "BTC-USDT",
                    "generated_at_ms": 2000,
                    "bars_by_market_type": {"spot_usdt": [{"timestamp_ms": 1000, "close": 100.0}]},
                    "latest_by_market_type": {"spot_usdt": {"timestamp_ms": 1000, "close": 100.0}},
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "run_summary.json").write_text(json.dumps({"asset": "BTC-USDT"}), encoding="utf-8")
    out_file = tmp_path / "site" / "index.html"

    result = write_dashboard_export(tmp_path, out_file, artifact_base_url="artifacts")

    html = out_file.read_text(encoding="utf-8")
    assert result == {
        "status": "OK",
        "dashboard_path": str(out_file.resolve()),
        "asset_count": 1,
        "artifact_count": 2,
    }
    assert 'const staticArtifactBase = "artifacts";' in html
    assert '"mode":"OBSERVED_PUBLIC_DATA"' in html
    assert str(tmp_path.resolve()) not in html


def test_write_dashboard_export_reports_missing_root(tmp_path: Path) -> None:
    result = write_dashboard_export(tmp_path / "missing", tmp_path / "index.html")

    assert result["status"] == "ERROR"
    assert result["error"].startswith("ARTIFACT_ROOT_NOT_FOUND:")


def test_safe_json_path_rejects_path_traversal(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(DashboardInputError, match="ARTIFACT_PATH_OUTSIDE_ROOT"):
        _safe_json_path(tmp_path, "../outside.json")


def test_safe_json_path_rejects_non_json_file(tmp_path: Path) -> None:
    note = tmp_path / "note.txt"
    note.write_text("ignore", encoding="utf-8")

    with pytest.raises(DashboardInputError, match="ARTIFACT_PATH_NOT_JSON"):
        _safe_json_path(tmp_path, "note.txt")


def test_serve_dashboard_reports_bind_failure(monkeypatch, tmp_path: Path) -> None:
    import crypto_composite.dashboard as dashboard_module

    def raise_permission_error(*args, **kwargs):
        raise PermissionError(10013, "forbidden")

    monkeypatch.setattr(dashboard_module, "ThreadingHTTPServer", raise_permission_error)

    with pytest.raises(DashboardBindError, match="DASHBOARD_BIND_FAILED"):
        serve_dashboard(tmp_path, host="127.0.0.1", port=8765)
