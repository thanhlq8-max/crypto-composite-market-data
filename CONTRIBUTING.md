# Contributing

Scope for v0.1 is intentionally narrow:

- public exchange connectors;
- normalized OHLCV, recent trades, orderbook, funding and open-interest snapshots;
- composite OHLCV artifacts;
- composite orderbook ladder artifacts;
- data-quality reporting;
- documentation and tests.

Out of scope:

- trading signals;
- order execution;
- private account APIs;
- leverage, position sizing, or portfolio advice;
- profitability claims.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```
