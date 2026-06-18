# Multi-symbol universe mode

Universe mode runs the same composite artifact pipeline over an explicit list of assets.

Example:

```bash
crypto-composite universe \
  --assets BTC-USDT,ETH-USDT,SOL-USDT \
  --venues binance,okx,bybit \
  --market-types spot_usdt,perp_usdt \
  --timeframes 15m,1h \
  --out-dir artifacts-universe
```

Output layout:

```text
artifacts-universe/
├── BTC-USDT/
│   ├── raw_scan_15m.json
│   ├── composite_ohlcv_15m.json
│   └── composite_orderbook_ladder_15m.json
├── ETH-USDT/
│   └── ...
└── universe_summary.json
```

`universe_summary.json` is an artifact index. It is designed for dashboards, notebooks, and CI smoke checks.

## Current scope

- Explicit asset list only.
- USDT pairs only.
- Binance / OKX / Bybit public endpoints only.
- Spot USDT and linear USDT perpetual markets.

## Non-goals

- Automatic listing discovery.
- Asset recommendations.
- Buy/sell rankings.
- Portfolio allocation.
- Trading performance reports.
