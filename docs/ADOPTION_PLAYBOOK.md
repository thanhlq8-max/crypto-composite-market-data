# Adoption playbook

This project should grow as a reusable market-data infrastructure package, not as a trading-signal product.

## Target users

- Data engineers who need repeatable public crypto market-data artifacts.
- Researchers who need venue coverage and dispersion checks before downstream analysis.
- Dashboard builders who want stable JSON files instead of exchange-specific payloads.
- Contributors who want small, testable connector and artifact tasks.

## Value proposition

`crypto-composite-market-data` answers practical data-quality questions:

- Which venues returned usable data?
- Is OHLCV coverage complete, partial, or weak?
- Are venue prices dispersed enough to warn downstream users?
- Is orderbook depth concentrated in one venue?
- Which symbols in a universe produced usable artifacts?

## Do not market as

- a trading bot;
- a buy/sell signal engine;
- a market-maker detector;
- a profitability system;
- financial advice.

## 30-day adoption plan

1. Keep the PyPI package install path working.
2. Keep the [repository-hosted dashboard screenshot](assets/dashboard-overview.png) aligned with the synthetic sample artifacts.
3. Adapt [Why composite public market data](WHY_COMPOSITE_MARKET_DATA.md) for an independent public technical channel.
4. Open 5 beginner-friendly issues from `docs/GOOD_FIRST_ISSUES.md`.
5. Ask users to share generated `data_quality.json` and `universe_summary.json` examples.

## 60-day adoption plan

1. Add one new public exchange connector.
2. Add CSV or DuckDB export.
3. Add artifact schema validation.
4. Add a minimal static dashboard frontend.
5. Collect user feedback in GitHub Discussions or Issues.

## Useful interaction prompts

Use concrete, non-trading prompts when sharing the project:

- "Can this artifact format fit your research/dashboard pipeline?"
- "Which exchange connector should be added next?"
- "What data-quality fields are missing for your workflow?"
- "Would CSV or DuckDB export be more useful than JSON only?"
