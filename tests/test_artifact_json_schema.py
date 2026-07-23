"""The committed sample artifacts must conform to the committed JSON Schemas.

This locks the artifact contract: a schema drift or a generator change that
breaks a downstream consumer fails here. Uses the optional ``jsonschema`` dep,
which is installed for development/CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crypto_composite import schema_validation

pytest.importorskip("jsonschema")

_SAMPLE_ROOT = Path(__file__).resolve().parent.parent / "examples" / "sample_artifacts"


def _sample_json_files() -> list[Path]:
    return sorted(_SAMPLE_ROOT.rglob("*.json"))


def test_sample_artifacts_exist() -> None:
    assert _SAMPLE_ROOT.is_dir()
    assert _sample_json_files(), "expected committed sample artifacts to validate against"


def test_all_committed_schemas_are_valid_json_schema() -> None:
    import jsonschema

    for name in schema_validation.available_schemas():
        schema = schema_validation.load_schema(name)
        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)  # raises on an invalid schema


@pytest.mark.parametrize("path", _sample_json_files(), ids=lambda p: p.name)
def test_sample_artifact_matches_its_schema(path: Path) -> None:
    name = schema_validation.schema_name_for_filename(path.name)
    if name is None:
        pytest.skip(f"{path.name} has no committed schema (combined/unschematized)")
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = schema_validation.validate(name, data)
    assert errors == [], f"{path.name} violates {name} schema: {errors}"


def test_at_least_one_of_each_core_schema_is_exercised() -> None:
    covered = {
        schema_validation.schema_name_for_filename(path.name)
        for path in _sample_json_files()
    }
    covered.discard(None)
    for expected in ("run_summary", "data_quality", "composite_ohlcv", "composite_orderbook_ladder"):
        assert expected in covered, f"no sample artifact exercises the {expected} schema"


def test_filename_mapping_distinguishes_combined_from_per_timeframe() -> None:
    m = schema_validation.schema_name_for_filename
    assert m("composite_ohlcv_15m.json") == "composite_ohlcv"
    assert m("composite_orderbook_ladder_1h.json") == "composite_orderbook_ladder"
    assert m("run_summary.json") == "run_summary"
    # Combined files nest under timeframe keys and are intentionally unschematized.
    assert m("composite_ohlcv.json") is None
    assert m("composite_orderbook_ladder.json") is None
    assert m("something_else.json") is None


def test_broken_artifact_is_reported() -> None:
    # Missing the required "status" field on a data-quality report.
    broken = {"15m": {"asset": "BTC-USDT", "venues_requested": [], "venues_ok": [],
                      "venues_failed": [], "market_types": [], "timeframe": "15m",
                      "missing_sources": [], "overall_quality": 0.9}}
    errors = schema_validation.validate("data_quality", broken)
    assert errors, "expected a schema violation for the missing 'status' field"
