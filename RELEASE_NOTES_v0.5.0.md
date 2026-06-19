# v0.5.0 â€” Artifact quality scoring

## Added

- Added `crypto-composite score-artifacts --artifact-root ...`.
- Added optional `--write` mode to create `quality_score.json` inside the artifact root.
- Added `crypto_composite.artifact_quality` for reproducible artifact quality scoring.
- Added tests for single-asset scoring, universe scoring, write mode, and CLI error behavior.
- Added `docs/ARTIFACT_QUALITY_SCORE.md`.

## Scope boundary

This release scores generated market-data artifacts only. It does not add trading signals, execution instructions, private account APIs, position sizing, financial advice, profitability claims, or market-maker intent claims.