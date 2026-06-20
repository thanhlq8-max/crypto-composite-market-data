# Artifact contract

This document describes the artifact contract emitted by package version `0.8.0`.

Artifacts do not currently contain a `schema_version` field. Consumers should use the installed package version as the compatibility reference and run `validate-artifacts` before consuming a directory.

## Validate before use

```bash
crypto-composite validate-artifacts --artifact-root artifacts-universe
```

The validator checks required files, JSON syntax, required top-level fields, timeframe coverage, raw-scan data groups when a raw scan is present, and universe asset-directory references. Missing required fields are reported in each error's `missing_fields` list. It does not certify market accuracy or interpret artifacts as trading signals.

## Single-asset directory

```text
artifacts/
|-- raw_scan_<timeframe>.json
|-- composite_ohlcv_<timeframe>.json
|-- composite_orderbook_ladder_<timeframe>.json
|-- composite_ohlcv.json
|-- composite_orderbook_ladder.json
|-- data_quality.json
`-- run_summary.json
```

The normal pipeline writes every file shown above. A minimal offline consumer fixture may omit `raw_scan_<timeframe>.json`; when a raw scan is present, the validator requires its `data` object to contain `ohlcv`, `trades`, `orderbooks`, `funding`, and `open_interest` groups.

### `run_summary.json`

Top-level fields:

- `asset`: normalized asset label such as `BTC-USDT`;
- `venues`: requested public venues;
- `market_types`: requested market types;
- `timeframes`: requested timeframes;
- `outputs`: generated filenames grouped by artifact type;
- `data_quality_by_timeframe`: scan-quality summaries; and
- `limitations`: explicit usage boundaries.

### `raw_scan_<timeframe>.json`

Contains the normalized public scan result for one timeframe. Its `data` object groups `ohlcv`, `trades`, `orderbooks`, `funding`, and `open_interest`. It may also contain connector errors and a `quality_report`.

### `composite_ohlcv_<timeframe>.json`

Contains one composite context with:

- `asset`, `timeframe`, `generated_at_ms`, and `expected_venues`;
- `bars_by_market_type`;
- `latest_by_market_type`;
- `status_by_market_type`;
- `coverage_by_market_type`; and
- `notes`.

Each composite bar includes OHLC values, median and volume-weighted close, total volumes, venue count and weights, coverage, price dispersion, and data quality.

### `composite_orderbook_ladder_<timeframe>.json`

Contains composite ladders keyed by market type. Each ladder records the reference price, bucket size, venue coverage, bid and ask levels, depth totals, depth imbalance, status, and notes.

Ladder levels include price bounds, quote depth, contributing venues, HHI concentration, persistence, spoof-risk proxy, and vacuum score. These are public snapshot diagnostics, not private orderflow or execution signals.

### Combined and quality files

- `composite_ohlcv.json`: timeframe keys mapped to composite OHLCV contexts.
- `composite_orderbook_ladder.json`: timeframe keys mapped to composite ladders.
- `data_quality.json`: timeframe keys mapped to scan-quality reports.

## Universe directory

```text
artifacts-universe/
|-- <ASSET>/
|   `-- <single-asset files>
`-- universe_summary.json
```

`universe_summary.json` records:

- `assets`, `venues`, `market_types`, and `timeframes`;
- `asset_count`;
- `asset_results`, including each asset's `artifact_dir`, outputs, quality summary, or error;
- `errors`;
- `outputs`; and
- `limitations`.

The validator follows each successful `asset_results[*].artifact_dir` and validates that directory as a single-asset artifact set.

## Compatibility rule

Consumers should tolerate additional object fields, but must not infer missing required files or rename fields. A future breaking contract change requires release notes and an explicit schema-version strategy before implementation.
