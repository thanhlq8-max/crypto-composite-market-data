# v0.11.0 - Coinbase Exchange Spot Connector

## Added

- Added optional `coinbase` venue support for Coinbase Exchange public spot market-data endpoints.
- Added `src/crypto_composite/connectors/coinbase.py` for public spot OHLCV, recent trades, and level-2 orderbook snapshots.
- Added mocked parser and connector-contract tests for Coinbase.
- Added `docs/COINBASE_CONNECTOR.md`.

## Scope

Coinbase support is spot-only in this release. The connector does not add private account APIs, authenticated requests, order placement, derivatives, rankings, predictions, trading signals, execution instructions, position sizing, profitability claims, or financial advice.

## Validation

Expected local checks:

```bash
py -m compileall src tests
py -m pytest -q
py -m build
```