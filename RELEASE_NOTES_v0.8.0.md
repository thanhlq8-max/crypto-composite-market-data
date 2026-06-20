# v0.8.0 - Observed Market Structure Dashboard V2

## Added

- Added `/api/dashboard-snapshot` for artifact-derived price, public-depth, zone, and methodology context.
- Added observed bid/ask liquidity concentration and public-depth vacuum zones.
- Added evidence grades that distinguish corroborated, venue-concentrated, and limited public-depth observations.
- Added spot/perpetual composite-close dislocation context without convergence claims.
- Added `dashboard-export` for a static Dashboard V2 HTML file with embedded analytical data.

## Changed

- Replaced the artifact-health-only frontend with asset, timeframe, and market filters, price and depth visuals, practical-zone tables, freshness, and methodology panels.
- Updated the GitHub Pages workflow to deploy the static Dashboard V2 export.
- Expanded checked-in synthetic orderbook fixtures so the public demo renders practical zones.

## Validation

- Python compile check.
- Full pytest suite.
- Source distribution and wheel build.
- Live public BTC-USDT spot/perpetual smoke run.
- Desktop and narrow-viewport browser checks with no console warnings or errors.

## Scope

This release remains public-data infrastructure. Evidence grades describe source corroboration only. It does not add trading signals, recommendations, predictions, hidden-liquidity claims, market-maker intent claims, position sizing, execution, or financial advice. The release and demo do not establish external adoption or Claude for Open Source eligibility.
