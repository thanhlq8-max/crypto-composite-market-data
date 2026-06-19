from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from crypto_composite.artifact_quality import score_artifact_root
from crypto_composite.artifact_validator import validate_artifact_root


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
