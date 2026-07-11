# PROJECT_STATE — crypto-composite-market-data

> Source of truth for AI-assisted sessions. Read this BEFORE any task. Update at the end of every significant session.

## OBJECTIVE

Public multi-exchange crypto market-data composite toolkit: normalized OHLCV / trades / orderbook artifacts from public Binance, OKX, Bybit (+ optional Coinbase Exchange, Kraken spot) endpoints. Data infrastructure only.

## LOCKED_DECISIONS

- LD-1 Public REST endpoints only. No private account, order, or execution APIs. Ever.
- LD-2 No trading semantics: no signals, entries/exits, SL/TP, position sizing, ranking, prediction, or profitability claims — in code, artifacts, docs, and wording.
- LD-3 Artifacts are reproducible JSON (+ CSV export); dashboard is read-only and local.
- LD-4 LFX alignment layer is monitor-only wording (`ADAPTED_MONITOR_ONLY`); it must never create routes, targets, or signals.
- LD-5 Explicit asset universes only; no automatic listing discovery.
- LD-6 Coverage denominator counts only venues capable of the market type (spot-only venues excluded from perp expectations). Decided 2026-07-11.
- LD-7 Composite status/coverage are judged on the last CLOSED bar (`is_closed`); `latest_by_market_type` stays the freshest bar. Decided 2026-07-11.
- LD-8 Ladder persistence carry-over reads the per-timeframe ladder artifact (keyed by market_type), never the combined per-timeframe-keyed file. Decided 2026-07-11.

## BUG_MEMORY

- BM-1 (fixed 2026-07-11) Shape mismatch: `pipeline.run_composite` fed the combined `composite_orderbook_ladder.json` (keyed by timeframe) into `_previous_lookup` (expects market_type keys) → persistence carry-over silently never fired. Pattern to watch: artifact files with different top-level key shapes passed across module boundaries without a shape assert.
- BM-2 (fixed 2026-07-11) Coverage penalized perp when spot-only venues (coinbase/kraken) were in `expected_venues` → status could never reach OK with 5 venues. Pattern: shared denominator across heterogeneous capabilities.
- BM-3 (fixed 2026-07-11) Status computed from in-progress candle → dispersion inflated on exactly the bar deciding status. Pattern: fetch-time skew leaking into quality metrics.
- BM-4 (open, MINOR) `utils.quote_volume` raises on `price<=0`; one bad record still drops the whole venue×market_type block in `_scan_venue`. Root-cause fix = per-record skip in connector parse loops.
- BM-5 (open, semantic) Per-venue `data_quality` constants (0.78–0.95) are undocumented INFERENCE exported as data.

## CURRENT_STATE (2026-07-11)

- Version 0.18.2 + audit branch (P0/P1 fixes, see CHANGELOG "Unreleased" once released).
- Tests: 107 passed locally (pytest, Python 3.10). Ruff clean (E701/E702 ignored by config — see follow-ups).
- CI: 3.10–3.13 matrix, ruff + compileall + pytest + build.
- `requires-python >= 3.10` (validated by full suite on 3.10).

## EVIDENCE_LEVELS

- Engines/pipeline/CLI: E3 (local test suite).
- Connector parsers: E3-mocked only. NOT validated against live 2026 exchange schemas this session.
- GitHub Pages demo + CI on GitHub: not re-verified this session.

## REVIEW_LENS

Python 3.10+, public exchange REST APIs (Binance/OKX/Bybit/Coinbase/Kraken), data-quality semantics, artifact schema stability, OSS packaging.

## NEXT_ALLOWED_WORK

- Live smoke test of connectors against current exchange schemas (record evidence).
- BM-4 root-cause fix (per-record skip) + tests.
- Remove ruff E701/E702 exception via a dedicated style-only PR; consider mypy.
- P2 backlog: 4h/1d timeframes, Parquet export, extract `dashboard_frontend` HTML to template file.
- Document basis for per-venue `data_quality` constants or derive them.

## NEXT_FORBIDDEN_WORK

- No new venues until coverage semantics (LD-6) ship in a release.
- No trading-semantics features of any kind (LD-2).
- No mass style refactor mixed with behavior changes.
