# v0.18.0 - Research Dataset Report

## Added

- Added `crypto-composite research-report` to generate a static research dataset report and companion `research_summary.json`.
- Added market microstructure rows covering composite OHLCV status, latest close, price dispersion, public orderbook status, depth totals, and imbalance.
- Added observed public-depth evidence rows with corroborated, concentrated, and limited zone counts plus nearest bid/ask concentration context.
- Updated `crypto-composite sample-report` to write `research_report.html` and `research_summary.json` alongside the artifact quality report and static dashboard.
- Updated the manual GitHub Pages workflow to use `research_report.html` as the demo landing page.

## Boundary

This release remains public-data and research-only. It does not add trading signals, asset rankings, predictions, private APIs, order execution, position sizing, profitability claims, or financial advice.
