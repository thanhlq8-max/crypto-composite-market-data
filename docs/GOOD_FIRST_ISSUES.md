# Good first issues backlog

Use this file to seed GitHub Issues. Keep each issue small, testable, and aligned with the no-signal/no-execution boundary.

## Connector tasks

### Add Coinbase public spot connector

Scope:
- public market data only;
- OHLCV/trades/orderbook where available;
- mocked parser tests;
- no private account API.

### Add Kraken public spot connector

Scope:
- public REST endpoints only;
- symbol mapping tests;
- partial-failure handling;
- no live-network CI tests.

## Artifact tasks

### Add CSV export for composite OHLCV

Scope:
- read existing `composite_ohlcv*.json`;
- write deterministic CSV;
- unit tests using sample artifacts.

### Add DuckDB export example

Scope:
- example script only;
- no hard dependency unless explicitly approved;
- document schema and query examples.

### Add artifact schema validation

Scope:
- validate generated JSON structure;
- no exchange network calls;
- fail clearly on missing required keys.

## Dashboard tasks

### Add a static HTML artifact index

Scope:
- read `/api/artifacts` output;
- display artifact paths and sizes;
- no trading widgets, no buy/sell labels.

### Add dashboard screenshots

Scope:
- use sample artifacts;
- document expected `/api/health` and `/api/artifacts` output;
- no live market claims.

## Documentation tasks

### Improve Windows quickstart

Scope:
- venv without PowerShell activation;
- `python.exe -m pip` commands;
- common port bind troubleshooting.

### Add "why composite market data" guide

Scope:
- explain venue coverage;
- explain price dispersion;
- explain book concentration;
- no trading edge claims.
