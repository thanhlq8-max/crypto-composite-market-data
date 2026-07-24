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
- BM-4 (fixed v0.19.0) One bad record (non-positive price, missing field, cast failure) dropped the whole venue×market_type block. Root-cause fix shipped: per-record skip via `parse_records` (candles/trades) in every connector, with regression coverage in `tests/test_connector_record_isolation.py`.
- BM-5 (documented v0.20.x) Per-venue `data_quality` constants are hand-set heuristic ordering priors, not measured accuracy. Traceability label recorded in `docs/DATA_QUALITY_CONSTANTS.md`; `connectors/base.py` points to it. Changing any value stays a scoped behavior change.
- BM-6 (fixed 2026-07-23) The Gate futures order book (dict-shaped `{p,s}` levels) still used a raw comprehension, so one malformed level raised and discarded the whole gate×perp block — the exact B4 class, missed when the Gate connector landed in v0.22.0. Fixed with `GateConnector._scaled_book_levels` (skip-and-scale). Pattern to watch: a new venue whose payload shape differs from the shared `parse_book_levels` helper needs its own per-record skip.
- BM-7 (fixed 2026-07-23) `requirements-dev.txt` pinned `ruff>=0.6` (no upper bound) and the ruff config set no explicit `select`, so CI floated to ruff 0.16 whose broader default rules failed the lint step on every job — turning all open Dependabot PRs (and fresh runs) red for a reason unrelated to their diff. Fixed by pinning `[tool.ruff.lint] select` to the intended rule set. Pattern to watch: linter/formatter version floats + implicit default rule sets make CI non-deterministic; pin the rules, not just the version.

## CURRENT_STATE (2026-07-23)

- Releasing 1.0.0: branch `release/v1.0.0` bumps `pyproject.toml` + `__init__.__version__` to 1.0.0, sets the Production/Stable classifier, and consolidates the CHANGELOG. `main` at this point has #83, #85, #86, #87 merged (Gate perp book fix, order-book record-isolation for every venue, live-verify evidence harness, mypy CI baseline, committed JSON Schema contract). Publish is manual (`workflow_dispatch`): TestPyPI → PyPI, then tag + release per `docs/RELEASE_CHECKLIST.md`.
- Since the 0.18.2 snapshot this file used to describe, v0.19.0–v0.22.0 shipped: B1–B4 fixes, OKX/Gate contract-unit corrections, coverage/closed-bar verdict integrity, per-venue token-bucket rate limiting + opt-in cache, WebSocket depth-lifecycle streaming, the Gate.io venue, CSV/Parquet export, and the `data_quality` constants traceability doc.
- Tests: 229 passed, 5 skipped locally (pytest, full dev env). CI: 3.10–3.13 matrix, ruff + mypy + compileall + pytest + build.
- Artifact contract now has committed JSON Schemas (`crypto_composite.artifact_schemas`), `validate-artifacts --json-schema` via the optional `[schema]` extra, a CI conformance test, and `docs/SCHEMA_STABILITY.md`.
- `requires-python >= 3.10` (validated by full suite on 3.10).

## EVIDENCE_LEVELS

- Engines/pipeline/CLI: E3 (local test suite).
- Connector parsers: E3-mocked, including per-record isolation for candles, trades,
  and every order book. A live-verification harness exists (`scripts/live_smoke.py
  --evidence-out`) but the E3→live promotion still needs a real network run whose
  dated `live_verification_<UTC>` record is committed.
- GitHub Pages demo + CI on GitHub: not re-verified this session.

## REVIEW_LENS

Python 3.10+, public exchange REST APIs (Binance/OKX/Bybit/Coinbase/Kraken), data-quality semantics, artifact schema stability, OSS packaging.

## NEXT_ALLOWED_WORK

- Run `scripts/live_smoke.py --evidence-out docs/live-verification` on a network host and commit the dated record to complete the E3→live connector promotion (harness + unit-scale check now in place).
- Schematize the remaining artifacts: the combined `composite_ohlcv.json` / `composite_orderbook_ladder.json` (timeframe-nested) and `zone_lifecycle*.json`.
- Tighten the mypy baseline toward `--strict` incrementally (per module) now that a clean baseline is enforced.
- v1.0.0: freeze schemas, confirm live-verified connectors, semver guarantees. See `docs/ROADMAP.md`.

## NEXT_FORBIDDEN_WORK

- No new venues until coverage semantics (LD-6) ship in a release.
- No trading-semantics features of any kind (LD-2).
- No mass style refactor mixed with behavior changes.
