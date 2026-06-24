# Roadmap

This roadmap keeps the project focused on reusable market-data infrastructure, not trading signals.

## v0.2 — Core contract hardening

Goal: make the public connector layer safer for downstream users.

- Domain-specific errors for unsupported venues and timeframes.
- Empty orderbook guards before composite ladder generation.
- Mocked connector parser tests for Binance / OKX / Bybit.
- Package-grade CI with editable install, console script checks, and wheel build.

## v0.3 — Multi-symbol universe artifacts

Goal: support explicit multi-asset research runs without turning the project into a signal scanner.

- `crypto-composite universe --assets BTC-USDT,ETH-USDT,SOL-USDT`.
- Per-asset artifact directories.
- `universe_summary.json` for data-quality and artifact discovery.
- No buy/sell ranking or performance claims.

## v0.4 — Artifact schema and reproducibility

Goal: make outputs stable enough for notebooks, dashboards, and downstream tools.

- Versioned artifact schemas.
- Manifest files with run inputs and generated filenames.
- Clear compatibility notes for future schema changes.
- Example notebooks that inspect data quality, not trading outcomes.

## v0.5 — Local data-quality dashboard

Goal: expose useful public-data diagnostics visually.

Candidate panels:

- Universe health.
- Venue coverage.
- Composite OHLCV viewer.
- Public orderbook ladder viewer.
- Spot/perp divergence context.
- Data-quality warnings.
- Artifact manifest browser.

Forbidden dashboard semantics:

- Buy/sell signals.
- Entry, stop-loss, or take-profit instructions.
- Profitability claims.
- Market-maker intent claims.

## v0.6 — Optional package distribution

Goal: make adoption easier.

- PyPI release after CI and packaging checks remain stable.
- Installation docs for `pip install crypto-composite-market-data`.
- Release notes with migration notes.

## v0.7 — Community-ready contribution surface

Goal: make the repository easy for external users and contributors to engage with.

- Issue templates for bugs, feature requests, and data-source requests.
- Pull request template with validation and boundary checks.
- Good-first-issue backlog for connectors, exports, docs, and dashboard API.
- Community growth documentation focused on data-quality and reproducible artifacts.
- External examples and tutorials that avoid trading-signal claims.


## v0.8-v0.9 ??? Shareable dashboard inspection artifacts

Goal: make generated public-data artifacts easier to inspect and share without creating trading signals.

- Static dashboard export for GitHub Pages or offline inspection.
- Dashboard snapshot API for artifact-derived price, depth, zone, and methodology context.
- Practical monitoring brief language remains descriptive and non-predictive.

## v0.10 - CSV artifact interoperability

Goal: make composite OHLCV artifacts easier to consume from spreadsheet, DuckDB, pandas, and notebooks.

- `crypto-composite export-ohlcv-csv --artifact-root ... --out-file ...`.
- Single-asset and universe artifact roots.
- One row per asset, timeframe, market type, and composite OHLCV bar.
- No ranking, signal, prediction, execution, or financial-advice semantics.

## v0.11 - Coinbase Exchange spot connector

Goal: expand public venue coverage without adding private account APIs, derivatives assumptions, or execution semantics.

- Optional `coinbase` venue.
- Public spot OHLCV, recent trades, and level-2 orderbook snapshots.
- `spot_usdt` only; no Coinbase perpetual/funding/open-interest support in this release.
- Mocked parser tests and connector contract tests.
- No ranking, signal, prediction, execution, or financial-advice semantics.
