# v0.9.0 - Practical Monitoring Brief Dashboard V3

## Added

- Added a structured `monitoring_brief` for each market context with DID / Past, DOING / Now, NEXT evidence, and Confidence / Risk sections.
- Added exact reference-relative location and nearest-edge distance for each observed zone.
- Added nearest bid/ask concentration context, public depth totals, depth imbalance, and evidence-grade counts to the dashboard snapshot.

## Changed

- Expanded the dashboard evidence sequence from three generic cards to four source-backed monitoring cards.
- Added zone location and distance columns to the practical-zone table.
- Updated CLI help, documentation, and the GitHub Pages workflow for Dashboard V3.

## Validation

- Full pytest suite and Python source compile.
- Source distribution and wheel build with a clean install smoke test.
- Live public-data artifact run and dashboard snapshot reconciliation.
- Desktop and narrow-viewport browser checks with console inspection.

## Scope

This release changes only dashboard analytics and presentation. It does not alter connectors, composite engines, trading behavior, risk behavior, or artifact generation. The monitoring brief is descriptive public-data context, not a signal, prediction, recommendation, hidden-liquidity claim, or market-maker intent claim.
