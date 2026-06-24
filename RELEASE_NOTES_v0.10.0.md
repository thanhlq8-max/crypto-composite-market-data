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