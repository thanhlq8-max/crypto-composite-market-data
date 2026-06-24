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
- No live API fetch, ranking, prediction, execution, or financial-advice semantics.

## v0.14 candidate — Checked-in demo/site polish

Goal: improve adoption evidence by making sample outputs and demo navigation easier to review from GitHub.

Candidate scope:

- Add or refresh checked-in sample report/dashboard outputs only if generated from existing sample artifacts.
- Document how to regenerate the sample report from a clean clone.
- Keep generated demo outputs clearly labeled as sample/illustrative artifacts.
- Ensure links from README, `docs/SAMPLE_REPORT.md`, and GitHub Pages docs are consistent.
- Do not fetch live APIs, add ranking, add prediction, add execution, or introduce financial-advice wording.

Acceptance:

- A new user can inspect sample artifacts, report HTML, and dashboard HTML without live API access.
- Regeneration commands are documented and tested or smoke-testable.
- Demo files are static and safe to publish through GitHub Pages.
- No runtime behavior change unless separately scoped.

## Long-term adoption track

Goal: grow the project as a credible open-source data-infrastructure utility.

- Keep issue backlog small, concrete, and contributor-friendly.
- Prefer docs, examples, artifact interoperability, and reproducibility before complex runtime expansion.
- Track real adoption evidence honestly: users, issues, forks, downloads, external examples, and integrations.
- Treat external maintainer-support programs as downstream opportunities, not as current eligibility claims.
