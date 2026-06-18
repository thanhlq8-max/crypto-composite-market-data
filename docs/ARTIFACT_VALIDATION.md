# Artifact validation

`crypto-composite validate-artifacts` checks generated JSON artifact structure before downstream use.

The validator is data-infrastructure only. It does not generate trading signals, execution instructions, position sizing, financial advice, or profitability claims.

## Validate a universe run

```bash
crypto-composite validate-artifacts --artifact-root artifacts-universe
```

Example output:

```json
{
  "status": "OK",
  "artifact_root": "artifacts-universe",
  "mode": "universe",
  "assets_checked": 3,
  "files_checked": 25,
  "errors": [],
  "warnings": []
}
```

## Validate a single-asset run

```bash
crypto-composite validate-artifacts --artifact-root artifacts
```

## What is checked

For universe roots, the validator checks:

- `universe_summary.json` exists and is valid JSON;
- `asset_results` is present;
- every successful asset entry points to an artifact directory;
- every asset directory has a valid single-asset artifact set.

For single-asset roots, the validator checks:

- `run_summary.json` exists and has a valid `timeframes` list;
- `data_quality.json` exists and is valid JSON;
- combined `composite_ohlcv.json` exists;
- combined `composite_orderbook_ladder.json` exists;
- each timeframe has `composite_ohlcv_<timeframe>.json`;
- each timeframe has `composite_orderbook_ladder_<timeframe>.json`.

## Status values

```text
OK    Required artifact structure is present.
WARN  Required files exist, but non-blocking warnings were found.
ERROR Required files are missing, invalid, or structurally unusable.
```

The CLI exits with code `1` only for `ERROR`.
