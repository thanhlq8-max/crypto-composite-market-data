# PROJECT_STATE — crypto-composite-market-data

> Source of truth for development sessions. Read this BEFORE any task. Update at the end of every significant session.

## OBJECTIVE

Public multi-exchange crypto market-data composite toolkit: normalized OHLCV / trades / orderbook artifacts from public Binance, OKX, Bybit (+ optional Coinbase Exchange, Kraken spot, Gate.io) endpoints. Data infrastructure only.

## LOCKED_DECISIONS

- LD-1 Public market-data endpoints only. No private account, order, or execution APIs. Ever.
- LD-2 No trading semantics: no signals, entries/exits, SL/TP, position sizing, ranking, prediction, or profitability claims — in code, artifacts, docs, and wording.
- LD-3 Artifacts are reproducible JSON (+ CSV/Parquet export); dashboard/report surfaces are read-only.
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
- BM-7 (fixed 2026-07-23) `requirements-dev.txt` floated Ruff while the config relied on implicit defaults, so a Ruff default-rule change made unrelated CI red. Fixed by pinning `[tool.ruff.lint] select` to the intended rule set. Pattern: linter/formatter version floats + implicit defaults make CI non-deterministic; pin behavior explicitly.

## CURRENT_STATE (2026-08-10)

- `main` package metadata is `version = "1.0.0"` with `Development Status :: 5 - Production/Stable`.
- The `v1.0.0` git ref is directly readable and contains package version `1.0.0`; therefore the stable tag exists.
- `main` is newer than the v1.0.0 tag and currently includes post-release dev/CI maintenance, including PR #94 and merged PR #95 (`ruff>=0.16.1`). These changes do not alter the v1.0.0 artifact contract by themselves.
- Whether a GitHub Release object or PyPI publication currently exists was not re-verified in this state-sync task; keep those facts `UNKNOWN` unless fresh authoritative evidence is collected.
- The stable artifact-schema policy remains in `docs/SCHEMA_STABILITY.md`; breaking schema changes require an explicit versioned decision.
- Live connector evidence is still incomplete at the source-of-truth level: the scripted harness exists, but a dated committed live-verification record remains the required promotion evidence.
- Historical test statement remains: 229 passed, 5 skipped locally before the 1.0.0 release-preparation sequence. Do not treat that historical count as fresh validation of current `main`.

## EVIDENCE_LEVELS

- Package/version state: E2/E3 repository evidence (`pyproject.toml`, readable `v1.0.0` ref).
- Engines/pipeline/CLI: historical E3 local-suite evidence; fresh current-main result required before new completion claims.
- Connector parsers: E3-mocked, including per-record isolation for candles, trades, and every order book.
- Live connectors: harness exists (`scripts/live_smoke.py --evidence-out`), but source-of-truth promotion remains pending a real dated network record committed under `docs/live-verification`.
- GitHub Pages/current CI/GitHub Release/PyPI state: UNKNOWN unless freshly re-verified for the specific claim.

## REVIEW_LENS

Python 3.10+, public exchange market-data APIs, data-quality semantics, artifact schema stability, reproducibility, OSS packaging, and post-1.0 compatibility discipline.

## NEXT_ALLOWED_WORK

- Run `scripts/live_smoke.py --evidence-out docs/live-verification` on a network host and commit the dated record to complete the mocked→live connector evidence promotion.
- Schematize the remaining combined/timeframe-nested and `zone_lifecycle*.json` artifacts without breaking the stable additive-only contract.
- Tighten the mypy baseline toward `--strict` incrementally, per module, with no mass refactor.
- Maintain post-1.0 compatibility and release hygiene; any new release requires fresh CI/build evidence and explicit release approval.
- Update this PROJECT_STATE whenever release/publication/live-verification evidence changes.

## NEXT_FORBIDDEN_WORK

- No trading-semantics features of any kind (LD-2).
- No private account/order/execution API integration (LD-1).
- No breaking stable artifact-schema change without an explicit versioned compatibility decision.
- No mass style/refactor change mixed with behavior changes.
- No claim that current `main`, GitHub Release, PyPI publication, Pages, or live connector status is verified without fresh evidence for that exact claim.
