# v0.17.0 - Dashboard Refresh Profile

Issue: #36

## Added

- Added `dashboard_profile.json` support for explicit dashboard primary timeframe, multi-timeframe list, and refresh cadence metadata.
- Added `crypto-composite dashboard-profile` to write dashboard profile metadata into an artifact root.
- Added `crypto-composite dashboard-refresh` to regenerate an explicit universe and rewrite a static dashboard on a fixed local cadence, with explicit bucket size required.
- Dashboard V3 now prefers the profile primary timeframe when present and displays the profile cadence.

## Fixed

- Fixed the remaining `docs/ROADMAP.md` mojibake heading noted in the v0.16.2 project state.
- Replaced dashboard middle-dot separators with ASCII-safe separators in generated HTML text.

## Boundary

This release remains public-data and monitor-only. It does not add trading signals, asset rankings, predictions, private APIs, order execution, position sizing, or financial advice.
