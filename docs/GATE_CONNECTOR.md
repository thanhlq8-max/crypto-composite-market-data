# Gate.io connector

Gate.io is an optional venue serving both public spot and USDT-settled
perpetual data. It is **not** in the default venue set — add it explicitly:

```bash
crypto-composite run \
  --asset BTC-USDT \
  --venues binance,okx,bybit,gate \
  --market-types spot_usdt,perp_usdt \
  --timeframes 15m \
  --out-dir artifacts
```

## Scope

- Asset input: `BASE-USDT`, for example `BTC-USDT`, mapped to the Gate.io
  `BASE_QUOTE` form (`BTC_USDT`) for both spot pairs and futures contracts.
- Public REST OHLCV, recent trades, level-2 orderbook snapshots, plus funding
  rate and open interest for perpetuals.
- Timeframes: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`.

## Units (live-verified 2026-07-12)

- **Spot** volumes and orderbook sizes are in base currency; the spot candle
  row order is `[ts, quote_volume, close, high, low, open, base_volume,
  closed]` (close precedes high/low/open, unlike most venues).
- **Perpetual** candle volume, trade size, orderbook size, and open interest
  are reported in **contracts**, not base currency. The connector scales them
  by the instrument `quanto_multiplier` (e.g. `BTC_USDT` = 0.0001 BTC),
  fetched once per contract and cached — the same contract-unit handling as
  the OKX SWAP connector. Futures trade `size` is signed (negative = taker
  sell); the connector takes the magnitude and records the aggressor side.

## Coverage note

Gate.io is perp-capable, so when it is included in a run the perpetual
coverage denominator counts it. Default runs (which do not include Gate.io)
are unchanged.

## Boundary

Public market data only. No private account APIs, order execution, or
financial advice.
