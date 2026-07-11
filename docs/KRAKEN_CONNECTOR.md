# Kraken public spot connector

Version: v0.12.0

`kraken` is an optional public spot venue for `crypto-composite-market-data`.

## Supported scope

- Market type: `spot_usdt` only.
- Asset input: `BASE-USDT`, for example `BTC-USDT`.
- BTC is mapped to Kraken's XBT pair naming for public REST requests.
- Timeframes: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`.
- Public REST OHLCV, recent trades, and level-2 orderbook snapshots.

## Unsupported scope

- Kraken private account APIs.
- Authenticated requests.
- Order placement or account operations.
- Kraken derivatives, funding, or open-interest data.
- Ranking, prediction, trading signals, execution logic, position sizing, or financial advice.

## Example

```bash
crypto-composite run \
  --asset BTC-USDT \
  --venues binance,okx,bybit,coinbase,kraken \
  --market-types spot_usdt \
  --timeframes 15m \
  --out-dir artifacts-spot
```

Kraken is intentionally optional. Default venue examples continue to use Binance, OKX, and Bybit unless the user explicitly requests additional spot venues.
