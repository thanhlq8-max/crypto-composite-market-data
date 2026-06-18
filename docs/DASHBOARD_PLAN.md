# Local dashboard plan

The dashboard should visualize artifact quality and public market-data structure. It should not become a trading terminal.

## Recommended architecture

```text
FastAPI app
├── artifact reader
├── JSON API endpoints
└── static frontend
```

## Candidate API endpoints

```text
/api/universe-summary
/api/assets
/api/assets/{asset}/timeframes
/api/assets/{asset}/{timeframe}/composite-ohlcv
/api/assets/{asset}/{timeframe}/orderbook-ladder
/api/assets/{asset}/{timeframe}/data-quality
```

## First dashboard panels

1. Universe health.
2. Venue coverage by asset.
3. Composite OHLCV latest status.
4. Orderbook ladder coverage and depth imbalance.
5. Artifact manifest / file browser.

## Wording guard

Use data-quality language:

- OK / partial / weak.
- Coverage.
- Dispersion.
- Public depth.
- Artifact generated / missing.

Do not use trading language:

- Buy / sell.
- Long / short now.
- Entry.
- Stop-loss / take-profit.
- Signal confidence.
