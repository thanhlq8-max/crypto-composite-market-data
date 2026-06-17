# Output artifacts

## Per-timeframe files

For timeframe `15m`, the CLI writes:

```text
raw_scan_15m.json
composite_ohlcv_15m.json
composite_orderbook_ladder_15m.json
```

## Combined files

```text
composite_ohlcv.json
composite_orderbook_ladder.json
data_quality.json
run_summary.json
```

## Suggested downstream use

- local research notebooks;
- market-data QA dashboards;
- public-data monitoring widgets;
- connector validation;
- exchange data comparison.

## Explicitly excluded downstream use

- automated order placement;
- account-level trading;
- position sizing;
- buy/sell recommendations;
- profitability claims.
