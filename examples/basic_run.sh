#!/usr/bin/env bash
set -euo pipefail

python -m crypto_composite.cli run \
  --asset BTC-USDT \
  --venues binance,okx,bybit \
  --market-types spot_usdt,perp_usdt \
  --timeframes 15m \
  --limit 300 \
  --depth 100 \
  --out-dir artifacts
