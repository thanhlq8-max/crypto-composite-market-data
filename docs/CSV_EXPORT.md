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