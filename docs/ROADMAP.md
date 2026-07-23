# Roadmap

This roadmap keeps the project focused on reusable public market-data infrastructure, artifact inspection, and adoption readiness. It is not a trading-signal, execution, ranking, prediction, or financial-advice roadmap.

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

## v0.4 — Artifact schema validation

Goal: make generated artifact folders structurally checkable before downstream use.

- `crypto-composite validate-artifacts --artifact-root ...`.
- Single-asset and universe artifact-root validation.
- Explicit errors and warnings for missing or malformed JSON files.
- Validator remains structural; it does not judge market direction or tradability.

## v0.5 — Artifact quality scoring

Goal: give users a compact, reproducible quality score for artifact inspection.

- `crypto-composite score-artifacts --artifact-root ... --write`.
- A-F artifact-quality grade derived from venue coverage, composite status, price dispersion, orderbook coverage, and existing data-quality status.
- `quality_score.json` for dashboards, reports, and CI inspection.
- No ranking, signal, prediction, execution, or financial-advice semantics.

## v0.6 — Static HTML artifact report

Goal: make generated public-data artifacts easier to inspect and share offline.

- `crypto-composite report --artifact-root ... --out-file report.html`.
- Static, dependency-light HTML report.
- Includes quality score, validation status, venue coverage, composite status, price dispersion, and artifact links.
- Inspection-only; no trading advice or predictive claims.

## v0.7 — Sample artifacts and GitHub Pages demo plan

Goal: make the repository easier to understand before users run live public API fetches.

- Checked-in synthetic or illustrative sample artifacts.
- GitHub Pages demo plan and sample artifact documentation.
- Contributor-facing docs for useful first issues and downstream examples.
- External examples and tutorials must avoid trading-performance claims.

## v0.8-v0.9 — Shareable dashboard inspection artifacts

Goal: make generated public-data artifacts easier to inspect and share without creating trading signals.

- Static dashboard export for GitHub Pages or offline inspection.
- Dashboard snapshot API for artifact-derived price, depth, zone, and methodology context.
- Practical monitoring brief language remains descriptive and non-predictive.
- Read-only dashboard and static export only; no private APIs or order APIs.

## v0.10 — CSV artifact interoperability

Goal: make composite OHLCV artifacts easier to consume from spreadsheet, DuckDB, pandas, and notebooks.

- `crypto-composite export-ohlcv-csv --artifact-root ... --out-file ...`.
- Single-asset and universe artifact roots.
- One row per asset, timeframe, market type, and composite OHLCV bar.
- No ranking, signal, prediction, execution, or financial-advice semantics.

## v0.11 — Coinbase Exchange spot connector

Goal: expand public venue coverage without adding private account APIs, derivatives assumptions, or execution semantics.

- Optional `coinbase` venue.
- Public spot OHLCV, recent trades, and level-2 orderbook snapshots.
- `spot_usdt` only; no Coinbase perpetual/funding/open-interest support in this release.
- Mocked parser tests and connector contract tests.
- No ranking, signal, prediction, execution, or financial-advice semantics.

## v0.12 — Kraken spot connector

Goal: expand optional public spot venue coverage while preserving the public-data-only boundary.

- Optional `kraken` venue.
- Public spot OHLCV, recent trades, and level-2 orderbook snapshots.
- `spot_usdt` only; no Kraken perpetual/funding/open-interest support in this release.
- Mocked parser tests and connector contract tests.
- No ranking, signal, prediction, execution, or financial-advice semantics.

## v0.13 — Offline sample report workflow

Goal: reduce first-run friction by letting users inspect checked-in sample artifacts before fetching live public data.

- `crypto-composite sample-report`.
- Validates `examples/sample_artifacts`.
- Computes artifact quality score.
- Writes static artifact report and dashboard HTML under `sample-report/`.
- GitHub Pages workflow builds the same report/dashboard from checked-in fixtures.
- No live API fetch, ranking, prediction, execution, or financial-advice semantics.

## v0.14 candidate — Live demo verification and sample-site polish

Goal: make the public demo easier to verify, reproduce, and use as an adoption asset.

Candidate scope:

- Verify the live GitHub Pages demo opens after deployment and links resolve.
- Keep the deployed demo generated from `examples/sample_artifacts` through `crypto-composite sample-report`.
- Document the current demo URL, local reproduction command, and release verification status consistently.
- Improve sample-site navigation only if it can be generated from existing synthetic fixtures.
- Do not fetch live APIs, add ranking, add prediction, add execution, or introduce financial-advice wording.

Acceptance:

- README, `docs/SAMPLE_REPORT.md`, and `docs/GITHUB_PAGES_DEMO.md` point to the same demo workflow and URL.
- A new user can inspect sample artifacts, report HTML, and dashboard HTML without live API access.
- Regeneration commands are documented and smoke-testable.
- No runtime behavior change unless separately scoped.

## Long-term adoption track

Goal: grow the project as a credible open-source data-infrastructure utility.

- Keep issue backlog small, concrete, and contributor-friendly.
- Prefer docs, examples, artifact interoperability, and reproducibility before complex runtime expansion.
- Track real adoption evidence honestly: users, issues, forks, downloads, external examples, and integrations.
- Treat external maintainer-support programs as downstream opportunities, not as current eligibility claims.


## v0.15.0 - Operational briefing report

- Add DID / DOING / NEXT MONITOR / KEY LEVELS / RISK CONTEXT to the static report.
- Derive the briefing only from existing composite OHLCV and public ladder artifacts.
- Keep the report monitor-only with no execution guidance or prediction.

## v0.23 → v1.0 — Stabilization and first stable release

After the v0.16–v0.22 feature track (venue expansion through Gate.io, WebSocket
depth-lifecycle streaming, CSV/Parquet export, dashboard exports), this track
hardens what shipped and prepares a stable 1.0 artifact contract. It stays inside
the locked boundary: public data only, no signals, predictions, ranking,
execution, or financial advice.

### v0.23 — Connector robustness parity

- Extend per-record isolation to every order-book path, not only candles/trades:
  one malformed public level must never discard a venue × market_type block.
- Order-book record-isolation regression tests for all venues — **delivered**
  (`binance`, `okx`, `bybit`, `coinbase`, `kraken`, and both Gate book shapes).
- Gate USDT-perp book skip-and-scale fix (dict-shaped `{p,s}` levels) — **delivered**.

### v0.24 — Live connector verification evidence

- Scripted, rate-limited live smoke test per venue against current exchange
  schemas; record dated evidence (units, field presence, contract multipliers).
  Tooling **delivered**: `scripts/live_smoke.py --evidence-out` writes a dated
  `live_verification_<UTC>` record and asserts a `quote/(base*close)` unit-scale
  ratio that catches a contract-unit regression.
- Promote connectors from E3-mocked to E3 + live-verified in `PROJECT_STATE.md`
  — **pending a real network run** committed as the evidence artifact.

### v0.25 — Type and style baseline

- Add mypy to CI — **delivered** (non-strict `[tool.mypy]` baseline over
  `src/crypto_composite`; the 15 defects it surfaced are fixed).
- Remove the ruff E701/E702 exception — **already done**: the config carries no
  such ignore and `ruff check` is clean, so there is nothing left to remove.
- Extract the inline `dashboard_frontend` HTML into a template file — **already
  done**: `dashboard_frontend.py` loads `templates/dashboard.html` via
  `importlib.resources`.

### v0.26 — Formal artifact schema and stability policy

- Turn the `docs/ARTIFACT_SCHEMA.md` contract into committed JSON Schema files and
  validate generated artifacts against them — **delivered**: Draft 2020-12 schemas
  for the core artifacts under `crypto_composite.artifact_schemas`,
  `validate-artifacts --json-schema` (optional `[schema]` extra), and a CI
  conformance test over the committed sample artifacts.
- Publish a schema-stability statement: additive-only artifact fields at 1.0 —
  **delivered** (`docs/SCHEMA_STABILITY.md`).
- Follow-ups: schematize the combined `composite_ohlcv.json` /
  `composite_orderbook_ladder.json` (timeframe-nested) and `zone_lifecycle*.json`.

### v1.0.0 — Stable public data-infrastructure release — in release

- Version bumped to `1.0.0`; artifact schema contract is additive-only from here
  (`docs/SCHEMA_STABILITY.md`); `data_quality` basis documented.
- Connectors validated by the mocked test suite; the live-verification harness
  (`scripts/live_smoke.py --evidence-out`) records dated live evidence out of band
  (still pending a committed network run).
- Reproducible sample and GitHub Pages demo verified per release.
- Semantic-version guarantees; new venues and exports remain additive behind the
  same no-trading-semantics boundary.
- Publish order: TestPyPI → PyPI (manual `workflow_dispatch`), then tag + release
  (`docs/RELEASE_CHECKLIST.md`).
