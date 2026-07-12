# Query artifacts with DuckDB

DuckDB reads the flat CSV/Parquet exports and the JSON artifacts directly —
no server, no schema migration. All examples below run against the checked-in
synthetic sample artifacts, so they work offline:

```bash
pip install duckdb
crypto-composite export-ohlcv-csv \
  --artifact-root examples/sample_artifacts \
  --out-file composite_ohlcv.csv
# Or, with the [parquet] extra installed:
crypto-composite export-ohlcv-parquet \
  --artifact-root examples/sample_artifacts \
  --out-file composite_ohlcv.parquet
```

## Coverage and dispersion overview

```sql
-- duckdb
SELECT
  asset,
  timeframe,
  market_type,
  count(*)                       AS bars,
  round(avg(coverage), 3)        AS avg_coverage,
  round(max(price_dispersion_pct), 4) AS worst_dispersion_pct,
  round(avg(data_quality), 3)    AS avg_quality
FROM 'composite_ohlcv.parquet'   -- or 'composite_ohlcv.csv'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
```

## Bars that would fail the OK gate

The status gates are documented in `STATUS_THRESHOLDS.md` (OK needs coverage
>= 0.67 and dispersion <= 0.08%):

```sql
SELECT asset, timeframe, market_type, timestamp_ms,
       coverage, price_dispersion_pct
FROM 'composite_ohlcv.parquet'
WHERE coverage < 0.67 OR price_dispersion_pct > 0.08
ORDER BY timestamp_ms;
```

## Venue weights from the embedded JSON column

```sql
SELECT
  timestamp_ms,
  market_type,
  json_extract(venue_weights_json, '$.binance') AS binance_w,
  json_extract(venue_weights_json, '$.okx')     AS okx_w,
  json_extract(venue_weights_json, '$.bybit')   AS bybit_w
FROM 'composite_ohlcv.parquet'
ORDER BY timestamp_ms
LIMIT 10;
```

## Ladder depth zones straight from the JSON artifact

`read_json_auto` unnests the per-timeframe ladder file (keys are market
types):

```sql
SELECT
  lvl.side,
  lvl.price_low,
  lvl.price_high,
  round(lvl.depth_quote, 0) AS depth_quote,
  lvl.venue_count,
  lvl.hhi
FROM (
  SELECT unnest(spot_usdt.bid_levels) AS lvl
  FROM read_json_auto('examples/sample_artifacts/BTC-USDT/composite_orderbook_ladder_15m.json')
)
ORDER BY lvl.depth_quote DESC
LIMIT 5;
```

## Same data in pandas

```python
import pandas as pd

frame = pd.read_parquet("composite_ohlcv.parquet")  # or pd.read_csv(...)
summary = (
    frame.groupby(["asset", "timeframe", "market_type"])
    .agg(bars=("timestamp_ms", "size"),
         avg_coverage=("coverage", "mean"),
         worst_dispersion_pct=("price_dispersion_pct", "max"))
    .round(4)
)
print(summary)
```

## Boundaries

These queries inspect generated public-data artifacts. They do not rank
assets, produce trading signals, predictions, or execution guidance — the
same boundaries as every other output of this package.
