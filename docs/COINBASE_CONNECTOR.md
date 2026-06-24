# Coinbase Exchange spot connector

`crypto-composite-market-data` supports Coinbase Exchange as an optional public spot data source.

## Supported scope

| Area | Status |
|---|---|
| Public spot OHLCV candles | Supported |
| Public recent trades | Supported |
| Public level-2 orderbook snapshots | Supported |
| Perpetual / derivatives market type | Not supported |
| Funding / open interest | Not supported |
| Private account APIs | Not supported |
| Orders / execution | Not supported |

## Example

Use Coinbase with spot-only market types:

```bash
crypto-composite run \
  --asset BTC-USDT \
  --venues binance,okx,bybit,coinbase \
  --market-types spot_usdt \
  --timeframes 15m \
  --out-dir artifacts-spot
```

Coinbase product IDs are resolved from `BASE-USDT` to `BASE-USDT`, for example `BTC-USDT`. The connector does not pre-verify exchange listing availability; unsupported products surface as public API fetch errors.

## Boundary

This connector is market-data infrastructure only. It does not create rankings, predictions, trading signals, execution instructions, position sizing, profitability claims, or financial advice.

