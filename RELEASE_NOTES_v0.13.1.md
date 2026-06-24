# v0.13.1 — Sample Report Windows Path Hotfix

## Summary

This maintenance release fixes Windows cross-drive handling in the offline sample-report workflow and links the live synthetic GitHub Pages demo from README/docs.

## Fixed

- Fall back to a `file://` artifact base URL when `sample-report` computes dashboard artifact links across different Windows drives.
- Add regression coverage for the cross-drive fallback path.
- Link the GitHub Pages synthetic demo from README and `docs/GITHUB_PAGES_DEMO.md`.

## Boundaries

- No connector behavior change.
- No composite logic change.
- No artifact schema change.
- No private APIs.
- No asset ranking, prediction, execution instruction, trading signal, or financial advice.
