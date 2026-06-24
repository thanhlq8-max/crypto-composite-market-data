$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Content
    )
    $parent = Split-Path -Parent $Path
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
}

Write-Utf8NoBom -Path "src\crypto_composite\artifact_csv.py" -Content @'
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from crypto_composite.artifact_validator import validate_artifact_root

NO_SIGNAL_BOUNDARY = "Composite OHLCV CSV export only; no trading signal, execution instruction, or financial advice."

CSV_COLUMNS = (
    "asset",
    "timeframe",
    "market_type",
    "timestamp_ms",
    "open",
    "high",
    "low",
    "close",
    "median_close",
    "vwap_close",
    "volume_base_total",
    "volume_quote_total",
    "venue_count",
    "coverage",
    "price_dispersion_pct",
    "data_quality",
    "venue_weights_json",
)


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _json_cell(value: Any) -> str:
    if not isinstance(value, (dict, list)):
        return ""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _csv_row(
    *,
    asset_label: str | None,
    timeframe_key: str,
    market_type: str,
    context: dict[str, Any],
    bar: dict[str, Any],
) -> dict[str, Any]:
    return {
        "asset": bar.get("asset") or context.get("asset") or asset_label or "",
        "timeframe": bar.get("timeframe") or context.get("timeframe") or timeframe_key,
        "market_type": bar.get("market_type") or market_type,
        "timestamp_ms": bar.get("timestamp_ms", ""),
        "open": bar.get("open", ""),
        "high": bar.get("high", ""),
        "low": bar.get("low", ""),
        "close": bar.get("close", ""),
        "median_close": bar.get("median_close", ""),
        "vwap_close": bar.get("vwap_close", ""),
        "volume_base_total": bar.get("volume_base_total", ""),
        "volume_quote_total": bar.get("volume_quote_total", ""),
        "venue_count": bar.get("venue_count", ""),
        "coverage": bar.get("coverage", ""),
        "price_dispersion_pct": bar.get("price_dispersion_pct", ""),
        "data_quality": bar.get("data_quality", ""),
        "venue_weights_json": _json_cell(bar.get("venue_weights")),
    }


def _asset_rows(asset_dir: Path, asset_label: str | None = None) -> list[dict[str, Any]]:
    combined = _as_mapping(_read_json(asset_dir / "composite_ohlcv.json"))
    rows: list[dict[str, Any]] = []
    for timeframe_key, context_value in sorted(combined.items()):
        context = _as_mapping(context_value)
        bars_by_market_type = _as_mapping(context.get("bars_by_market_type"))
        for market_type, bars_value in sorted(bars_by_market_type.items()):
            for bar_value in _as_list(bars_value):
                bar = _as_mapping(bar_value)
                if bar:
                    rows.append(
                        _csv_row(
                            asset_label=asset_label,
                            timeframe_key=str(timeframe_key),
                            market_type=str(market_type),
                            context=context,
                            bar=bar,
                        )
                    )
    return rows


def _universe_rows(root: Path) -> tuple[list[dict[str, Any]], int]:
    summary = _as_mapping(_read_json(root / "universe_summary.json"))
    asset_results = _as_mapping(summary.get("asset_results"))
    rows: list[dict[str, Any]] = []
    assets_checked = 0
    for asset, item_value in sorted(asset_results.items()):
        item = _as_mapping(item_value)
        if item.get("error"):
            continue
        artifact_dir = item.get("artifact_dir")
        if not isinstance(artifact_dir, str) or not artifact_dir.strip():
            continue
        asset_rows = _asset_rows(root / artifact_dir, str(asset))
        rows.extend(asset_rows)
        assets_checked += 1
    return rows, assets_checked


def write_composite_ohlcv_csv(artifact_root: str | Path, out_file: str | Path) -> dict[str, Any]:
    """Export generated composite OHLCV artifacts to a flat CSV file.

    The export preserves artifact inspection boundaries. It does not rank assets,
    generate predictions, produce trading signals, or create execution advice.
    """
    root = Path(artifact_root)
    csv_path = Path(out_file)
    validation = validate_artifact_root(root)
    result: dict[str, Any] = {
        "status": "OK",
        "artifact_root": str(root),
        "csv_path": str(csv_path),
        "row_count": 0,
        "assets_checked": 0,
        "errors": [],
        "warnings": [],
        "validation": validation,
        "boundaries": [NO_SIGNAL_BOUNDARY],
    }

    if validation.get("status") == "ERROR":
        result["status"] = "ERROR"
        result["errors"] = list(validation.get("errors", []))
        result["warnings"] = list(validation.get("warnings", []))
        return result

    if validation.get("mode") == "universe":
        rows, assets_checked = _universe_rows(root)
    else:
        rows = _asset_rows(root)
        assets_checked = 1 if rows else 0

    result["row_count"] = len(rows)
    result["assets_checked"] = assets_checked
    result["warnings"] = list(validation.get("warnings", []))
    if not rows:
        result["warnings"].append({"path": str(root / "composite_ohlcv.json"), "code": "NO_COMPOSITE_OHLCV_ROWS_EXPORTED"})

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)

    if validation.get("status") == "WARN" or result["warnings"]:
        result["status"] = "WARN"
    return result
'@

Write-Utf8NoBom -Path "tests\test_artifact_csv.py" -Content @'
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from crypto_composite import cli
from crypto_composite.artifact_csv import write_composite_ohlcv_csv


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _bar(asset: str, market_type: str, timestamp_ms: int, close: float) -> dict:
    return {
        "asset": asset,
        "timeframe": "15m",
        "market_type": market_type,
        "timestamp_ms": timestamp_ms,
        "open": close - 1.0,
        "high": close + 1.0,
        "low": close - 2.0,
        "close": close,
        "median_close": close,
        "vwap_close": close,
        "volume_base_total": 10.0,
        "volume_quote_total": close * 10.0,
        "venue_count": 3,
        "venue_weights": {"binance": 0.34, "bybit": 0.33, "okx": 0.33},
        "coverage": 1.0,
        "price_dispersion_pct": 0.04,
        "data_quality": 0.95,
    }


def _write_single_asset(root: Path, asset: str = "BTC-USDT") -> None:
    quality_report = {
        "asset": asset,
        "venues_requested": ["binance", "okx", "bybit"],
        "venues_ok": ["binance", "okx", "bybit"],
        "venues_failed": [],
        "market_types": ["spot_usdt", "perp_usdt"],
        "timeframe": "15m",
        "missing_sources": [],
        "overall_quality": 0.95,
        "status": "OK",
    }
    ohlcv_context = {
        "asset": asset,
        "timeframe": "15m",
        "generated_at_ms": 1700000000000,
        "expected_venues": ["binance", "okx", "bybit"],
        "bars_by_market_type": {
            "spot_usdt": [_bar(asset, "spot_usdt", 1699999100000, 100.7)],
            "perp_usdt": [_bar(asset, "perp_usdt", 1699999100000, 100.9)],
        },
        "latest_by_market_type": {
            "spot_usdt": {"price_dispersion_pct": 0.04},
            "perp_usdt": {"price_dispersion_pct": 0.05},
        },
        "status_by_market_type": {
            "spot_usdt": "COMPOSITE_DATA_OK",
            "perp_usdt": "COMPOSITE_DATA_OK",
        },
        "coverage_by_market_type": {"spot_usdt": 1.0, "perp_usdt": 1.0},
        "notes": [],
    }

    def ladder(market_type: str) -> dict:
        return {
            "asset": asset,
            "market_type": market_type,
            "generated_at_ms": 1700000000000,
            "reference_price": 100.0,
            "bucket_size": 1.0,
            "expected_venues": ["binance", "okx", "bybit"],
            "venue_count": 3,
            "coverage": 1.0,
            "bid_levels": [],
            "ask_levels": [],
            "top_bid_wall": None,
            "top_ask_wall": None,
            "bid_depth_total": 0.0,
            "ask_depth_total": 0.0,
            "depth_imbalance": 0.0,
            "status": "COMPOSITE_BOOK_OK",
            "notes": [],
        }

    ladder_document = {"spot_usdt": ladder("spot_usdt"), "perp_usdt": ladder("perp_usdt")}
    _write_json(
        root / "run_summary.json",
        {
            "asset": asset,
            "venues": ["binance", "okx", "bybit"],
            "market_types": ["spot_usdt", "perp_usdt"],
            "timeframes": ["15m"],
            "outputs": {},
            "data_quality_by_timeframe": {"15m": quality_report},
            "limitations": [],
        },
    )
    _write_json(root / "data_quality.json", {"15m": quality_report})
    _write_json(root / "composite_ohlcv.json", {"15m": ohlcv_context})
    _write_json(root / "composite_orderbook_ladder.json", {"15m": ladder_document})
    _write_json(root / "composite_ohlcv_15m.json", ohlcv_context)
    _write_json(root / "composite_orderbook_ladder_15m.json", ladder_document)


def test_export_single_asset_composite_ohlcv_csv(tmp_path: Path) -> None:
    _write_single_asset(tmp_path)
    out_file = tmp_path / "composite_ohlcv.csv"

    result = write_composite_ohlcv_csv(tmp_path, out_file)

    rows = list(csv.DictReader(out_file.open(encoding="utf-8")))
    assert result["status"] == "OK"
    assert result["row_count"] == 2
    assert {row["market_type"] for row in rows} == {"spot_usdt", "perp_usdt"}
    assert rows[0]["asset"] == "BTC-USDT"
    assert "venue_weights_json" in rows[0]
    assert "trading signal" in result["boundaries"][0]


def test_export_universe_composite_ohlcv_csv(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "universe_summary.json",
        {
            "assets": ["BTC-USDT", "ETH-USDT"],
            "venues": ["binance", "okx", "bybit"],
            "market_types": ["spot_usdt", "perp_usdt"],
            "timeframes": ["15m"],
            "asset_count": 2,
            "asset_results": {
                "BTC-USDT": {"artifact_dir": "BTC-USDT"},
                "ETH-USDT": {"artifact_dir": "ETH-USDT"},
            },
            "errors": [],
            "outputs": {},
            "limitations": [],
        },
    )
    _write_single_asset(tmp_path / "BTC-USDT", "BTC-USDT")
    _write_single_asset(tmp_path / "ETH-USDT", "ETH-USDT")
    out_file = tmp_path / "ohlcv.csv"

    result = write_composite_ohlcv_csv(tmp_path, out_file)

    rows = list(csv.DictReader(out_file.open(encoding="utf-8")))
    assert result["status"] == "OK"
    assert result["assets_checked"] == 2
    assert result["row_count"] == 4
    assert {row["asset"] for row in rows} == {"BTC-USDT", "ETH-USDT"}


def test_export_csv_returns_error_when_validation_fails(tmp_path: Path) -> None:
    result = write_composite_ohlcv_csv(tmp_path / "missing", tmp_path / "out.csv")

    assert result["status"] == "ERROR"
    assert result["errors"]
    assert not (tmp_path / "out.csv").exists()


def test_cli_export_ohlcv_csv_prints_json(monkeypatch, capsys, tmp_path: Path) -> None:
    _write_single_asset(tmp_path)
    out_file = tmp_path / "flat.csv"
    monkeypatch.setattr(
        "sys.argv",
        ["crypto-composite", "export-ohlcv-csv", "--artifact-root", str(tmp_path), "--out-file", str(out_file)],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "OK"
    assert payload["row_count"] == 2
    assert out_file.exists()


def test_cli_export_ohlcv_csv_exits_nonzero_on_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "crypto-composite",
            "export-ohlcv-csv",
            "--artifact-root",
            str(tmp_path / "missing"),
            "--out-file",
            str(tmp_path / "flat.csv"),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
'@

Write-Utf8NoBom -Path "docs\CSV_EXPORT.md" -Content @'
# CSV export

`crypto-composite-market-data` stores canonical artifacts as JSON. CSV export is an interoperability layer for spreadsheet, DuckDB, pandas, and simple downstream data-quality inspection workflows.

The exporter flattens generated `composite_ohlcv.json` files into one row per asset, timeframe, market type, and composite OHLCV bar.

## Command

```bash
crypto-composite export-ohlcv-csv \
  --artifact-root artifacts-universe \
  --out-file composite_ohlcv.csv
```

Single-asset artifact roots and universe artifact roots are both supported.

## Columns

```text
asset
timeframe
market_type
timestamp_ms
open
high
low
close
median_close
vwap_close
volume_base_total
volume_quote_total
venue_count
coverage
price_dispersion_pct
data_quality
venue_weights_json
```

`venue_weights_json` preserves the per-venue weighting map as compact JSON text so CSV consumers can keep venue contribution metadata without extra sidecar files.

## Boundary

CSV export is an artifact-inspection convenience only. It does not create rankings, predictions, trading signals, execution instructions, position sizing, profitability claims, or financial advice.
'@

Write-Utf8NoBom -Path "RELEASE_NOTES_v0.10.0.md" -Content @'
# v0.10.0 - Composite OHLCV CSV Export

## Added

- Added `crypto-composite export-ohlcv-csv` for flat CSV export of generated `composite_ohlcv.json` artifacts.
- Added `src/crypto_composite/artifact_csv.py` as a small artifact interoperability module.
- Added single-asset and universe CSV export tests.
- Added `docs/CSV_EXPORT.md`.

## Scope

This release exports existing artifact data only. It does not add connectors, exchange account APIs, trading signals, rankings, predictions, execution instructions, position sizing, profitability claims, or financial advice.

## Validation

Expected local checks:

```bash
py -m compileall src tests
py -m pytest -q
py -m build
```
'@

$patch = @'
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"PATCH_ANCHOR_NOT_FOUND: {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once("pyproject.toml", 'version = "0.9.0"', 'version = "0.10.0"')
replace_once("src/crypto_composite/__init__.py", '__version__ = "0.9.0"', '__version__ = "0.10.0"')

replace_once(
    "src/crypto_composite/cli.py",
    "from typing import Iterable\n\nfrom crypto_composite.artifact_quality import score_artifact_root, write_quality_score\n",
    "from typing import Iterable\n\nfrom crypto_composite.artifact_csv import write_composite_ohlcv_csv\nfrom crypto_composite.artifact_quality import score_artifact_root, write_quality_score\n",
)
replace_once(
    "src/crypto_composite/cli.py",
    '    report = sub.add_parser("report", help="Write a static HTML artifact quality report.")\n    report.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")\n    report.add_argument("--out-file", required=True, help="HTML report file to write.")\n',
    '    csv_export = sub.add_parser("export-ohlcv-csv", help="Export composite OHLCV artifacts to a flat CSV file.")\n    csv_export.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")\n    csv_export.add_argument("--out-file", required=True, help="CSV file to write.")\n\n    report = sub.add_parser("report", help="Write a static HTML artifact quality report.")\n    report.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")\n    report.add_argument("--out-file", required=True, help="HTML report file to write.")\n',
)
replace_once(
    "src/crypto_composite/cli.py",
    '    elif args.cmd == "report":\n        report_result = write_static_report(args.artifact_root, args.out_file)\n        print(json.dumps(report_result, indent=2, sort_keys=True))\n        if report_result["status"] == "ERROR":\n            parser.exit(1)\n',
    '    elif args.cmd == "export-ohlcv-csv":\n        export_result = write_composite_ohlcv_csv(args.artifact_root, args.out_file)\n        print(json.dumps(export_result, indent=2, sort_keys=True))\n        if export_result["status"] == "ERROR":\n            parser.exit(1)\n    elif args.cmd == "report":\n        report_result = write_static_report(args.artifact_root, args.out_file)\n        print(json.dumps(report_result, indent=2, sort_keys=True))\n        if report_result["status"] == "ERROR":\n            parser.exit(1)\n',
)

replace_once(
    "README.md",
    '## Static HTML report\n\nGenerate a shareable artifact-quality report:\n\n```bash\ncrypto-composite report --artifact-root artifacts-universe --out-file report.html\n```\n\nThe report summarizes quality score, venue coverage, composite OHLCV status, orderbook status, price dispersion, validator warnings/errors, and JSON artifact links. It is an inspection page only; it is not a trading signal, prediction, execution instruction, or financial-advice document.\n\nSee [docs/STATIC_REPORT.md](docs/STATIC_REPORT.md).\n\n## Local dashboard API\n',
    '## Static HTML report\n\nGenerate a shareable artifact-quality report:\n\n```bash\ncrypto-composite report --artifact-root artifacts-universe --out-file report.html\n```\n\nThe report summarizes quality score, venue coverage, composite OHLCV status, orderbook status, price dispersion, validator warnings/errors, and JSON artifact links. It is an inspection page only; it is not a trading signal, prediction, execution instruction, or financial-advice document.\n\nSee [docs/STATIC_REPORT.md](docs/STATIC_REPORT.md).\n\n## CSV export\n\nExport composite OHLCV artifacts to a flat CSV file for spreadsheet, DuckDB, pandas, or notebook inspection:\n\n```bash\ncrypto-composite export-ohlcv-csv \\\n  --artifact-root artifacts-universe \\\n  --out-file composite_ohlcv.csv\n```\n\nThe export writes one row per asset, timeframe, market type, and composite OHLCV bar. It preserves venue contribution metadata in `venue_weights_json` and remains an artifact-inspection output only.\n\nSee [docs/CSV_EXPORT.md](docs/CSV_EXPORT.md).\n\n## Local dashboard API\n',
)
replace_once(
    "README.md",
    '- [docs/STATIC_REPORT.md](docs/STATIC_REPORT.md)\n- [docs/TUTORIAL_CONSUME_ARTIFACTS.md](docs/TUTORIAL_CONSUME_ARTIFACTS.md)\n',
    '- [docs/STATIC_REPORT.md](docs/STATIC_REPORT.md)\n- [docs/CSV_EXPORT.md](docs/CSV_EXPORT.md)\n- [docs/TUTORIAL_CONSUME_ARTIFACTS.md](docs/TUTORIAL_CONSUME_ARTIFACTS.md)\n',
)

with Path("docs/ROADMAP.md").open("a", encoding="utf-8") as handle:
    handle.write(
        "\n\n## v0.8-v0.9 — Shareable dashboard inspection artifacts\n\n"
        "Goal: make generated public-data artifacts easier to inspect and share without creating trading signals.\n\n"
        "- Static dashboard export for GitHub Pages or offline inspection.\n"
        "- Dashboard snapshot API for artifact-derived price, depth, zone, and methodology context.\n"
        "- Practical monitoring brief language remains descriptive and non-predictive.\n\n"
        "## v0.10 — CSV artifact interoperability\n\n"
        "Goal: make composite OHLCV artifacts easier to consume from spreadsheet, DuckDB, pandas, and notebooks.\n\n"
        "- `crypto-composite export-ohlcv-csv --artifact-root ... --out-file ...`.\n"
        "- Single-asset and universe artifact roots.\n"
        "- One row per asset, timeframe, market type, and composite OHLCV bar.\n"
        "- No ranking, signal, prediction, execution, or financial-advice semantics.\n"
    )
'@
$patch | py -

Write-Host "v0.10.0 CSV export patch applied."
Write-Host "Run: py -m compileall src tests; py -m pytest -q; py -m build"
