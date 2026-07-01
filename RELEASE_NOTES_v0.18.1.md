# v0.18.1 - LFX Alignment Contract

## Added

- Added a structured `lfx_alignment` contract to the dashboard snapshot and research summary.
- Added per-market `lfx_mission_control.rows` object lists for MM Mission, TRADER Mode, NEXT Scenario, DID / Past, DOING / Now, KEY Zones, INV / Release, and Confidence / Risk.
- Added `docs/LFX_ALIGNMENT.md` to document how the allowed LFX-2 v8.1-D monitor-only rows map to public artifact fields.
- Added a dashboard LFX mission-control table plus copyable mission-control readout text.
- Added LFX alignment and mission-control sections to the static research dataset report.

## Boundary

This release keeps LFX-style behavior surveillance as public artifact review only. It does not add trading signals, asset rankings, predictions, private APIs, order execution, entry/exit instructions, position sizing, real market-maker inventory claims, hidden-liquidity claims, or financial advice.
