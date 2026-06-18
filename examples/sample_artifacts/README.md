# Sample artifacts

These files are illustrative examples of the artifact structure produced by `crypto-composite-market-data`.

They are not live market data and must not be used for trading decisions.

Included examples:

```text
examples/sample_artifacts/
├── universe_summary.json
├── data_quality.json
├── BTC-USDT/
│   ├── composite_ohlcv_15m.json
│   ├── composite_orderbook_ladder_15m.json
│   ├── data_quality.json
│   └── run_summary.json
└── ETH-USDT/
    ├── composite_ohlcv_15m.json
    ├── composite_orderbook_ladder_15m.json
    ├── data_quality.json
    └── run_summary.json
```

Use these files to test dashboard artifact browsing without calling live exchange APIs.
