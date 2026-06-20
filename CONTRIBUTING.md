# Contributing

Thanks for contributing to `crypto-composite-market-data`.

This project is intentionally scoped as public market-data infrastructure. Contributions should improve reliable data collection, composite artifacts, data-quality reporting, packaging, documentation, or local artifact inspection.

## In scope

- Public exchange connectors.
- Normalized OHLCV, recent trades, orderbook, funding and open-interest snapshots.
- Composite OHLCV artifacts.
- Composite orderbook ladder artifacts.
- Data-quality reporting.
- Multi-symbol universe runs.
- Read-only dashboard/API tooling for generated artifacts.
- Documentation, examples, tests, packaging and CI.

## Out of scope

- Trading signals.
- Order execution.
- Private account APIs.
- Leverage, position sizing, or portfolio advice.
- Financial advice.
- Market-maker intent claims.
- Profitability or statistical-edge claims.

## Development setup

```bash
git clone https://github.com/thanhlq8-max/crypto-composite-market-data.git
cd crypto-composite-market-data
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m pytest -q
```

## Validation before pull requests

Run:

```bash
python -m compileall src
python -m pytest -q
python -m build
```

## Good first contributions

- Add mocked parser tests for an existing connector.
- Add CSV export for composite OHLCV.
- Add a DuckDB export example without a mandatory runtime dependency.

## Connector contribution checklist

For a new public venue connector:

- Use official public API documentation.
- Do not require private credentials.
- Normalize output into existing dataclasses.
- Add mocked response tests.
- Handle empty orderbooks and partial/missing fields.
- Document rate limits and endpoint caveats.
- Preserve the no-signal, no-execution, no-financial-advice boundary.

## Pull request expectations

A good pull request should include:

- a concise problem statement;
- a narrow scope;
- tests or documentation updates;
- validation commands run locally;
- no generated build folders, local patch files, secrets, or private artifacts.
