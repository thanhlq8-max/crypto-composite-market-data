# Release Notes - v0.12.0

## Summary

v0.12.0 adds an optional Kraken public spot connector.

## Added

- `src/crypto_composite/connectors/kraken.py`.
- Optional `kraken` venue registration.
- Kraken `spot_usdt` symbol mapping.
- Mocked parser tests for public OHLCV, recent trades, and orderbook payloads.
- Spot-only symbol mapping test for Kraken.
- Kraken connector documentation.

## Scope boundary

- Public REST data only.
- `spot_usdt` only.
- No private APIs.
- No authenticated requests.
- No order placement.
- No ranking, prediction, trading-signal behavior, execution logic, position sizing, or financial advice.

## Validation

Run before commit/release:

```bash
python -m compileall src tests
python -m pytest -q
python -m build
```
