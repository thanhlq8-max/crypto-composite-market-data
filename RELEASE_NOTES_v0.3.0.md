# v0.3.0 — Release readiness and starter dashboard API

## Added

- Read-only local dashboard API over Python stdlib HTTP.
- `crypto-composite dashboard` CLI command.
- Artifact index endpoint at `/api/artifacts`.
- Individual JSON artifact endpoint at `/api/artifact?path=<relative-json-path>`.
- TestPyPI publishing workflow using GitHub Actions trusted publishing.
- Packaging guide for TestPyPI/PyPI release preparation.
- Example universe configuration and illustrative sample artifacts.

## Changed

- CI test matrix now includes Python 3.13.
- Package version advanced to `0.3.0`.

## Removed

- Removed committed patch file from repository source tree.

## Boundaries

The dashboard API is a read-only artifact viewer. It does not emit buy/sell signals, rankings, order execution instructions, position sizing, or financial advice.
