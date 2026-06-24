# v0.16.2 - Operational Briefing Card Separator Encoding Hotfix

## Fixed

- Replaced the non-ASCII briefing card title separator with ASCII-safe ` / ` to prevent mojibake in generated static HTML.
- Updated the report regression test to assert the encoding-safe card title.

## Boundary

- Monitor-only public market-data report.
- No trade call, execution instruction, position sizing, prediction, ranking, or financial advice.
- No connector, composite engine, or artifact schema change.
