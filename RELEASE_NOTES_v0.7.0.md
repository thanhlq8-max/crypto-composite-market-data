# v0.7.0 - Community-ready artifact inspection

## Added

- Added a read-only local dashboard frontend for artifact health, file sizes, quality rows, manifests, and JSON inspection.
- Added a deterministic two-asset sample fixture, consumer example, tutorial, and dashboard screenshot.
- Added issue forms, a pull request template, a code of conduct, and a downstream use-case evidence form.
- Added artifact schema, Windows quickstart, composite-methodology, community-growth, and GitHub Pages demo documentation.
- Added a manual-only GitHub Pages workflow that builds, validates, scores, and renders the synthetic sample fixture.

## Changed

- **Breaking:** `/api/artifacts` now returns `artifacts` as objects with `path` and `size_bytes` fields instead of path strings.
- Expanded artifact validation with required-field checks and explicit `missing_fields` details.
- Made the static-report forbidden-word guard token-aware so identifiers such as `outputs` do not trigger the standalone `TP` rule.

## Removed

- Removed the invalid root-level `examples/sample_artifacts/data_quality.json`; quality files remain inside each asset directory.

## Migration

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

## Scope

This release does not add connectors, trading signals, execution instructions, position sizing, predictions, profitability claims, or financial advice. The GitHub Pages workflow is manual and release preparation does not deploy it. These changes do not establish external adoption or Claude for Open Source eligibility.
