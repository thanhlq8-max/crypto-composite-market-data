"""Offline coverage for the live_smoke evidence writer.

`scripts/live_smoke.py` itself hits live endpoints and is not run in CI, but the
`_write_evidence` record format is a committable artifact, so it gets a network-
free regression test. The script lives under scripts/ (not the package), so it is
loaded by path.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "live_smoke.py"


def _load_live_smoke():
    spec = importlib.util.spec_from_file_location("live_smoke", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_write_evidence_emits_json_and_markdown(tmp_path) -> None:
    live_smoke = _load_live_smoke()
    results = [
        ("binance:spot_usdt:ohlcv", "PASS", "20 bars, last close=63000.0, qv/(base*close)~1.001"),
        ("okx:perp_usdt:orderbook", "FAIL", "crossed book"),
    ]

    md_path = live_smoke._write_evidence(str(tmp_path), "BTC-USDT", "15m", results, passed=1)

    assert md_path.exists()
    assert md_path.suffix == ".md"

    json_files = list(tmp_path.glob("live_verification_*.json"))
    assert len(json_files) == 1
    payload = json.loads(json_files[0].read_text(encoding="utf-8"))

    assert payload["asset"] == "BTC-USDT"
    assert payload["timeframe"] == "15m"
    assert payload["summary"] == {"passed": 1, "total": 2}
    assert [check["status"] for check in payload["checks"]] == ["PASS", "FAIL"]
    assert payload["boundary"].startswith("Public market data only")
