# Release Notes - v0.13.0

## Summary

v0.13.0 adds an offline sample artifact report workflow for first-run user inspection.

## Added

- `crypto-composite sample-report` CLI command.
- `src/crypto_composite/sample_workflow.py` helper module.
- `docs/SAMPLE_REPORT.md` usage guide.
- Tests for the sample workflow and CLI wiring.

## Behavior

The command reads an existing artifact root, validates it, computes quality scoring, and writes:

```text
sample-report/artifact_report.html
sample-report/dashboard.html
```

It uses `examples/sample_artifacts` by default and does not fetch live public exchange data.

## Boundary

No trading signal, execution instruction, prediction, position sizing, private exchange-account API, or financial advice behavior is added.
