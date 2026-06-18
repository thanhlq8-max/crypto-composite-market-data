from __future__ import annotations

import json
from pathlib import Path

import pytest

from crypto_composite import cli
from crypto_composite.artifact_validator import validate_artifact_root


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_single_asset_artifacts(root: Path, asset: str = "BTC-USDT") -> None:
    _write_json(root / "run_summary.json", {"asset": asset, "timeframes": ["15m"]})
    _write_json(root / "data_quality.json", {"15m": {"status": "OK"}})
    _write_json(root / "composite_ohlcv.json", {"15m": {"status_by_market_type": {}}})
    _write_json(root / "composite_orderbook_ladder.json", {"15m": {"status": "COMPOSITE_BOOK_OK"}})
    _write_json(root / "composite_ohlcv_15m.json", {"asset": asset})
    _write_json(root / "composite_orderbook_ladder_15m.json", {"asset": asset})


def test_validate_universe_artifacts_ok(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "universe_summary.json",
        {
            "assets": ["BTC-USDT", "ETH-USDT"],
            "asset_results": {
                "BTC-USDT": {"artifact_dir": "BTC-USDT"},
                "ETH-USDT": {"artifact_dir": "ETH-USDT"},
            },
        },
    )
    _write_single_asset_artifacts(tmp_path / "BTC-USDT", "BTC-USDT")
    _write_single_asset_artifacts(tmp_path / "ETH-USDT", "ETH-USDT")

    result = validate_artifact_root(tmp_path)

    assert result["status"] == "OK"
    assert result["mode"] == "universe"
    assert result["assets_checked"] == 2
    assert result["errors"] == []


def test_validate_single_asset_missing_timeframe_file_reports_error(tmp_path: Path) -> None:
    _write_single_asset_artifacts(tmp_path)
    (tmp_path / "composite_ohlcv_15m.json").unlink()

    result = validate_artifact_root(tmp_path)

    assert result["status"] == "ERROR"
    assert any(error["code"] == "MISSING_JSON_FILE" for error in result["errors"])


def test_validate_artifacts_rejects_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "run_summary.json").write_text("{not-json", encoding="utf-8")

    result = validate_artifact_root(tmp_path)

    assert result["status"] == "ERROR"
    assert result["errors"][0]["code"] == "INVALID_JSON"


def test_cli_validate_artifacts_prints_json(monkeypatch, capsys, tmp_path: Path) -> None:
    _write_single_asset_artifacts(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["crypto-composite", "validate-artifacts", "--artifact-root", str(tmp_path)],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "OK"
    assert payload["mode"] == "single_asset"


def test_cli_validate_artifacts_exits_nonzero_on_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["crypto-composite", "validate-artifacts", "--artifact-root", str(tmp_path / "missing")],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
