# v0.14.1 â€” Operational Context Render Hotfix

## Summary

This release fixes the v0.14.0 static report implementation so the LFX-style operational context section is actually rendered in `artifact_report.html`.

## Fixed

- Render the `Operational context` section in the static artifact report.
- Add regression assertions for `OBSERVATION READY`, `Operator mode`, `Monitor-only public data`, and market-type rows.

## Boundaries

- Static report and test hotfix only.
- No trading signal, execution instruction, ranking, prediction, private API, or financial advice.
- No connector, composite engine, artifact schema, or dashboard runtime behavior change.
