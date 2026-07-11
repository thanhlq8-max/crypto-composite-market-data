# Changelog

All notable changes to this project. Release notes were previously kept as per-version `RELEASE_NOTES_v*.md` files at the repository root; they are consolidated here.

## v0.18.2 - LFX Zone Review Objects

### Added

- Added `lfx_zone_review` to every observed public-depth zone.
- Added LFX-style zone role, review value, density-reference context, counterflow refresh check, and boundary text.
- Added the zone-level LFX review value to the dashboard observed-zones table and copyable observed-zones text.
- Added `lfx_zone_review` to `research_summary.json` observed-zone objects and static report zone evidence text.
- Updated dashboard, research report, and LFX alignment docs for the new zone-level object contract.

### Boundary

This release keeps zone review descriptive and public-artifact only. It does not add trading signals, asset rankings, predictions, route or target creation, hidden-liquidity claims, private-flow claims, order execution, position sizing, or financial advice.

## v0.18.1 - LFX Alignment Contract

### Added

- Added a structured `lfx_alignment` contract to the dashboard snapshot and research summary.
- Added per-market `lfx_mission_control.rows` object lists for MM Mission, TRADER Mode, NEXT Scenario, DID / Past, DOING / Now, KEY Zones, INV / Release, and Confidence / Risk.
- Added `docs/LFX_ALIGNMENT.md` to document how the allowed LFX-2 v8.1-D monitor-only rows map to public artifact fields.
- Added a dashboard LFX mission-control table plus copyable mission-control readout text.
- Added LFX alignment and mission-control sections to the static research dataset report.

### Boundary

This release keeps LFX-style behavior surveillance as public artifact review only. It does not add trading signals, asset rankings, predictions, private APIs, order execution, entry/exit instructions, position sizing, real market-maker inventory claims, hidden-liquidity claims, or financial advice.

## v0.18.0 - Research Dataset Report

### Added

- Added `crypto-composite research-report` to generate a static research dataset report and companion `research_summary.json`.
- Added market microstructure rows covering composite OHLCV status, latest close, price dispersion, public orderbook status, depth totals, and imbalance.
- Added observed public-depth evidence rows with corroborated, concentrated, and limited zone counts plus nearest bid/ask concentration context.
- Updated `crypto-composite sample-report` to write `research_report.html` and `research_summary.json` alongside the artifact quality report and static dashboard.
- Updated the manual GitHub Pages workflow to use `research_report.html` as the demo landing page.

### Boundary

This release remains public-data and research-only. It does not add trading signals, asset rankings, predictions, private APIs, order execution, position sizing, profitability claims, or financial advice.

## v0.17.0 - Dashboard Refresh Profile

Issue: #36

### Added

- Added `dashboard_profile.json` support for explicit dashboard primary timeframe, multi-timeframe list, and refresh cadence metadata.
- Added `crypto-composite dashboard-profile` to write dashboard profile metadata into an artifact root.
- Added `crypto-composite dashboard-refresh` to regenerate an explicit universe and rewrite a static dashboard on a fixed local cadence, with explicit bucket size required.
- Dashboard V3 now prefers the profile primary timeframe when present and displays the profile cadence.

### Fixed

- Fixed the remaining `docs/ROADMAP.md` mojibake heading noted in the v0.16.2 project state.
- Replaced dashboard middle-dot separators with ASCII-safe separators in generated HTML text.

### Boundary

This release remains public-data and monitor-only. It does not add trading signals, asset rankings, predictions, private APIs, order execution, position sizing, or financial advice.

## v0.16.2 - Operational Briefing Card Separator Encoding Hotfix

### Fixed

- Replaced the non-ASCII briefing card title separator with ASCII-safe ` / ` to prevent mojibake in generated static HTML.
- Updated the report regression test to assert the encoding-safe card title.

### Boundary

- Monitor-only public market-data report.
- No trade call, execution instruction, position sizing, prediction, ranking, or financial advice.
- No connector, composite engine, or artifact schema change.

## v0.16.1 â€” Operational Briefing Cards Render Hotfix

### Fixed

- Renders per-asset operational briefing cards above the existing inspection table.
- Adds explicit tests for briefing card layout, monitor-only boundary wording, and asset/timeframe/market card headers.

### Boundary

- Presentation-only report hotfix.
- No connector, composite engine, artifact schema, private API, prediction, ranking, execution, or financial-advice behavior change.

## v0.15.0 — Operational Briefing Report

### Added

- Static artifact report now includes an LFX-style Operational briefing section.
- Briefing rows include DID, DOING, NEXT MONITOR, KEY LEVELS, RISK CONTEXT, and Operator mode.
- Briefing is derived from existing composite OHLCV and public orderbook ladder artifacts.
- Tests assert the new briefing section and preserve the forbidden-language guard.

### Boundaries

- Public artifact data only.
- No private API.
- No order placement.
- No execution guidance.
- No position sizing.
- No prediction or ranking.
- No financial advice.

## v0.14.1 â€” Operational Context Render Hotfix

### Summary

This release fixes the v0.14.0 static report implementation so the LFX-style operational context section is actually rendered in `artifact_report.html`.

### Fixed

- Render the `Operational context` section in the static artifact report.
- Add regression assertions for `OBSERVATION READY`, `Operator mode`, `Monitor-only public data`, and market-type rows.

### Boundaries

- Static report and test hotfix only.
- No trading signal, execution instruction, ranking, prediction, private API, or financial advice.
- No connector, composite engine, artifact schema, or dashboard runtime behavior change.

## v0.13.1 — Sample Report Windows Path Hotfix

### Summary

This maintenance release fixes Windows cross-drive handling in the offline sample-report workflow and links the live synthetic GitHub Pages demo from README/docs.

### Fixed

- Fall back to a `file://` artifact base URL when `sample-report` computes dashboard artifact links across different Windows drives.
- Add regression coverage for the cross-drive fallback path.
- Link the GitHub Pages synthetic demo from README and `docs/GITHUB_PAGES_DEMO.md`.

### Boundaries

- No connector behavior change.
- No composite logic change.
- No artifact schema change.
- No private APIs.
- No asset ranking, prediction, execution instruction, trading signal, or financial advice.

## Release Notes - v0.13.0

### Summary

v0.13.0 adds an offline sample artifact report workflow for first-run user inspection.

### Added

- `crypto-composite sample-report` CLI command.
- `src/crypto_composite/sample_workflow.py` helper module.
- `docs/SAMPLE_REPORT.md` usage guide.
- Tests for the sample workflow and CLI wiring.

### Behavior

The command reads an existing artifact root, validates it, computes quality scoring, and writes:

```text
sample-report/artifact_report.html
sample-report/dashboard.html
```

It uses `examples/sample_artifacts` by default and does not fetch live public exchange data.

### Boundary

No trading signal, execution instruction, prediction, position sizing, private exchange-account API, or financial advice behavior is added.

## Release Notes - v0.12.0

### Summary

v0.12.0 adds an optional Kraken public spot connector.

### Added

- `src/crypto_composite/connectors/kraken.py`.
- Optional `kraken` venue registration.
- Kraken `spot_usdt` symbol mapping.
- Mocked parser tests for public OHLCV, recent trades, and orderbook payloads.
- Spot-only symbol mapping test for Kraken.
- Kraken connector documentation.

### Scope boundary

- Public REST data only.
- `spot_usdt` only.
- No private APIs.
- No authenticated requests.
- No order placement.
- No ranking, prediction, trading-signal behavior, execution logic, position sizing, or financial advice.

### Validation

Run before commit/release:

```bash
python -m compileall src tests
python -m pytest -q
python -m build
```

## v0.11.0 - Coinbase Exchange Spot Connector

### Added

- Added optional `coinbase` venue support for Coinbase Exchange public spot market-data endpoints.
- Added `src/crypto_composite/connectors/coinbase.py` for public spot OHLCV, recent trades, and level-2 orderbook snapshots.
- Added mocked parser and connector-contract tests for Coinbase.
- Added `docs/COINBASE_CONNECTOR.md`.

### Scope

Coinbase support is spot-only in this release. The connector does not add private account APIs, authenticated requests, order placement, derivatives, rankings, predictions, trading signals, execution instructions, position sizing, profitability claims, or financial advice.

### Validation

Expected local checks:

```bash
py -m compileall src tests
py -m pytest -q
py -m build
```

## v0.10.0 - Composite OHLCV CSV Export

### Added

- Added `crypto-composite export-ohlcv-csv` for flat CSV export of generated `composite_ohlcv.json` artifacts.
- Added `src/crypto_composite/artifact_csv.py` as a small artifact interoperability module.
- Added single-asset and universe CSV export tests.
- Added `docs/CSV_EXPORT.md`.

### Scope

This release exports existing artifact data only. It does not add connectors, exchange account APIs, trading signals, rankings, predictions, execution instructions, position sizing, profitability claims, or financial advice.

### Validation

Expected local checks:

```bash
py -m compileall src tests
py -m pytest -q
py -m build
```

## v0.9.0 - Practical Monitoring Brief Dashboard V3

### Added

- Added a structured `monitoring_brief` for each market context with DID / Past, DOING / Now, NEXT evidence, and Confidence / Risk sections.
- Added exact reference-relative location and nearest-edge distance for each observed zone.
- Added nearest bid/ask concentration context, public depth totals, depth imbalance, and evidence-grade counts to the dashboard snapshot.

### Changed

- Expanded the dashboard evidence sequence from three generic cards to four source-backed monitoring cards.
- Added zone location and distance columns to the practical-zone table.
- Updated CLI help, documentation, and the GitHub Pages workflow for Dashboard V3.

### Validation

- Full pytest suite and Python source compile.
- Source distribution and wheel build with a clean install smoke test.
- Live public-data artifact run and dashboard snapshot reconciliation.
- Desktop and narrow-viewport browser checks with console inspection.

### Scope

This release changes only dashboard analytics and presentation. It does not alter connectors, composite engines, trading behavior, risk behavior, or artifact generation. The monitoring brief is descriptive public-data context, not a signal, prediction, recommendation, hidden-liquidity claim, or market-maker intent claim.

## v0.8.0 - Observed Market Structure Dashboard V2

### Added

- Added `/api/dashboard-snapshot` for artifact-derived price, public-depth, zone, and methodology context.
- Added observed bid/ask liquidity concentration and public-depth vacuum zones.
- Added evidence grades that distinguish corroborated, venue-concentrated, and limited public-depth observations.
- Added spot/perpetual composite-close dislocation context without convergence claims.
- Added `dashboard-export` for a static Dashboard V2 HTML file with embedded analytical data.

### Changed

- Replaced the artifact-health-only frontend with asset, timeframe, and market filters, price and depth visuals, practical-zone tables, freshness, and methodology panels.
- Updated the GitHub Pages workflow to deploy the static Dashboard V2 export.
- Expanded checked-in synthetic orderbook fixtures so the public demo renders practical zones.

### Validation

- Python compile check.
- Full pytest suite.
- Source distribution and wheel build.
- Live public BTC-USDT spot/perpetual smoke run.
- Desktop and narrow-viewport browser checks with no console warnings or errors.

### Scope

This release remains public-data infrastructure. Evidence grades describe source corroboration only. It does not add trading signals, recommendations, predictions, hidden-liquidity claims, market-maker intent claims, position sizing, execution, or financial advice. The release and demo do not establish external adoption.

## v0.7.0 - Community-ready artifact inspection

### Added

- Added a read-only local dashboard frontend for artifact health, file sizes, quality rows, manifests, and JSON inspection.
- Added a deterministic two-asset sample fixture, consumer example, tutorial, and dashboard screenshot.
- Added issue forms, a pull request template, a code of conduct, and a downstream use-case evidence form.
- Added artifact schema, Windows quickstart, composite-methodology, community-growth, and GitHub Pages demo documentation.
- Added a manual-only GitHub Pages workflow that builds, validates, scores, and renders the synthetic sample fixture.

### Changed

- **Breaking:** `/api/artifacts` now returns `artifacts` as objects with `path` and `size_bytes` fields instead of path strings.
- Expanded artifact validation with required-field checks and explicit `missing_fields` details.
- Made the static-report forbidden-word guard token-aware so identifiers such as `outputs` do not trigger the standalone `TP` rule.

### Removed

- Removed the invalid root-level `examples/sample_artifacts/data_quality.json`; quality files remain inside each asset directory.

### Migration

Before:

```python
for path in payload["artifacts"]:
    inspect(path)
```

After:

```python
for artifact in payload["artifacts"]:
    path = artifact["path"]
    size_bytes = artifact["size_bytes"]
    inspect(path, size_bytes)
```

### Scope

This release does not add connectors, trading signals, execution instructions, position sizing, predictions, profitability claims, or financial advice. The GitHub Pages workflow is manual and release preparation does not deploy it. These changes do not establish external adoption.

## v0.6.0 - Static HTML artifact report

### Added

- Added `crypto-composite report` CLI command.
- Added static HTML artifact quality report generation.
- Added asset-level and timeframe-level quality tables in the report.
- Added validator warning/error display in the report.
- Added JSON artifact file links in the report.
- Added documentation for static report usage.

### Scope

This release does not add trading signals, execution instructions, position sizing, predictions, profitability claims, or financial advice.

## v0.5.1 - Source rendering hotfix

### Fixed

- Normalized repository text-file handling with `.gitattributes`.
- Kept package metadata aligned at `0.5.1`.
- Removed BOM risk from package version metadata.

### Scope

This release does not change artifact validation, artifact scoring, connector behavior, dashboard behavior, or any trading-related logic.

## v0.5.0 â€” Artifact quality scoring

### Added

- Added `crypto-composite score-artifacts --artifact-root ...`.
- Added optional `--write` mode to create `quality_score.json` inside the artifact root.
- Added `crypto_composite.artifact_quality` for reproducible artifact quality scoring.
- Added tests for single-asset scoring, universe scoring, write mode, and CLI error behavior.
- Added `docs/ARTIFACT_QUALITY_SCORE.md`.

### Scope boundary

This release scores generated market-data artifacts only. It does not add trading signals, execution instructions, private account APIs, position sizing, financial advice, profitability claims, or market-maker intent claims.

## v0.4.0 â€” Artifact schema validator

### Added

- Added `crypto-composite validate-artifacts --artifact-root ...`.
- Added `crypto_composite.artifact_validator` for validating generated JSON artifact structure.
- Added validation docs in `docs/ARTIFACT_VALIDATION.md`.
- Added tests for valid universe artifacts, missing required files, invalid JSON, and CLI output.

### Scope boundary

This release validates artifact structure only. It does not add trading signals, execution, private account APIs, position sizing, financial advice, or profitability claims.

﻿# v0.3.4 â€” Repository hygiene and formatted maintainer files

### Changed

- Reformatted `README.md`, `pyproject.toml`, GitHub Actions workflows, Dependabot config, `.gitignore`, and development requirements into maintainable multi-line files.
- Added project URLs to package metadata.
- Aligned package version metadata to `0.3.4`.
- Removed accidentally committed local patch artifacts when present.

### Unchanged boundaries

- No trading signals.
- No order execution.
- No private account APIs.
- No financial advice.
- No profitability or statistical-edge claim.

## v0.3.3 — Maintainer readiness and adoption docs

### Changed

- Added maintainer-facing release checklist.
- Added adoption playbook for growing the project as data infrastructure.
- Added good-first-issues backlog to make contribution entry points clearer.
- Added `.gitignore` rules for local patch and distribution artifacts.
- Clarified README references for contribution and roadmap materials.

### Unchanged boundaries

- No trading signals.
- No order execution.
- No private account APIs.
- No financial advice.
- No profitability or statistical-edge claim.

## v0.3.1 — Dashboard bind hardening

### Fixed

- Added a typed dashboard bind error for local socket binding failures.
- Improved CLI output when the dashboard port cannot be opened.
- Changed the documented dashboard example port to `18080` and documented alternate-port recovery for Windows `WinError 10013`.

### Boundary

This release does not add trading signals, order execution, position sizing, or financial advice.

## v0.3.0 — Release readiness and starter dashboard API

### Added

- Read-only local dashboard API over Python stdlib HTTP.
- `crypto-composite dashboard` CLI command.
- Artifact index endpoint at `/api/artifacts`.
- Individual JSON artifact endpoint at `/api/artifact?path=<relative-json-path>`.
- TestPyPI publishing workflow using GitHub Actions trusted publishing.
- Packaging guide for TestPyPI/PyPI release preparation.
- Example universe configuration and illustrative sample artifacts.

### Changed

- CI test matrix now includes Python 3.13.
- Package version advanced to `0.3.0`.

### Removed

- Removed committed patch file from repository source tree.

### Boundaries

The dashboard API is a read-only artifact viewer. It does not emit buy/sell signals, rankings, order execution instructions, position sizing, or financial advice.

## v0.2.0 — CI, connector contracts, and universe mode

### Added

- Hardened CI with editable install, CLI entrypoint checks, and package build validation.
- Typed connector and scan input errors for unsupported venues and timeframes.
- Empty-orderbook guards for public orderbook snapshots.
- Offline connector contract tests for Binance, OKX, and Bybit parser behavior.
- Multi-symbol universe mode via `crypto-composite universe`.
- Documentation for useful outputs, multi-symbol artifacts, roadmap, and dashboard direction.

### Boundaries

- No trading signals.
- No order execution.
- No financial advice.
- No private orderflow or market-maker intent claim.
- No profitability or statistical-edge claim.

## v0.1.0 — Initial public market-data composite toolkit

Initial public release.

### Includes

- Binance / OKX / Bybit public REST connectors.
- Composite OHLCV artifact builder.
- Composite orderbook ladder artifact builder.
- Data-quality reporting.
- CLI pipeline.
- Tests and CI.

### Non-goals

- No trading signals.
- No order execution.
- No financial advice.
- No private orderflow or market-maker intent claim.
- No profitability or statistical-edge claim.
