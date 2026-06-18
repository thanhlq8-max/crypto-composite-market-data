# v0.4.0 â€” Artifact schema validator

## Added

- Added `crypto-composite validate-artifacts --artifact-root ...`.
- Added `crypto_composite.artifact_validator` for validating generated JSON artifact structure.
- Added validation docs in `docs/ARTIFACT_VALIDATION.md`.
- Added tests for valid universe artifacts, missing required files, invalid JSON, and CLI output.

## Scope boundary

This release validates artifact structure only. It does not add trading signals, execution, private account APIs, position sizing, financial advice, or profitability claims.
