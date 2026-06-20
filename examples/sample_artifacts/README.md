# Sample artifacts

These deterministic files form a minimal universe artifact tree accepted by the package validator and quality scorer.

They are synthetic, are not live market data, and must not be used for trading decisions.

```text
examples/sample_artifacts/
|-- universe_summary.json
|-- BTC-USDT/
|   |-- composite_ohlcv.json
|   |-- composite_ohlcv_15m.json
|   |-- composite_orderbook_ladder.json
|   |-- composite_orderbook_ladder_15m.json
|   |-- data_quality.json
|   `-- run_summary.json
`-- ETH-USDT/
    |-- composite_ohlcv.json
    |-- composite_ohlcv_15m.json
    |-- composite_orderbook_ladder.json
    |-- composite_orderbook_ladder_15m.json
    |-- data_quality.json
    `-- run_summary.json
```

Validate and score the fixture without calling exchange APIs:

```bash
crypto-composite validate-artifacts --artifact-root examples/sample_artifacts
crypto-composite score-artifacts --artifact-root examples/sample_artifacts
```

Use these files for dashboard browsing, report generation, tutorials, and downstream consumer tests.
