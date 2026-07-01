# LFX-2 alignment contract

This repository adapts the monitor-only display contract from `D:\github-tools\LFX-2\LFX-2_PROJECT_STATE_v8.1-D_CONTROL_OS_vNext_FULL_FINAL.md` and `LFX-2_v8.1-D-COUNTERFLOW-ROUTE-ORIGIN-TEXT.txt` to public crypto market-data artifacts.

It does not port the TradingView Pine implementation, XAUUSD-specific assumptions, private orderflow logic, route locks, target locks, or trade-command workflow. The repo uses the LFX-2 structure as a display and interpretation contract over generated JSON artifacts.

## Applied contract

| LFX-style row | Repo artifact basis | Repo output |
|---|---|---|
| MM Mission | Artifact status, zone evidence mix, public-depth context | `lfx_mission_control.rows` |
| TRADER Mode | OHLCV status, book status, observed zone availability | `lfx_mission_control.rows` |
| NEXT Scenario | OHLCV status, book status, zone evidence mix, refresh profile | `monitoring_brief.next_evidence_check`, `zone_readout.next_check`, `lfx_mission_control.rows` |
| DID / Past | Latest two composite OHLCV bars and observed close change | `monitoring_brief.past`, `lfx_mission_control.rows` |
| DOING / Now | Latest composite bar, public orderbook ladder, nearest bid/ask concentration | `monitoring_brief.now`, `observed_zones`, `lfx_mission_control.rows` |
| KEY Zones | Top depth bucket, maximum vacuum bucket, evidence grade, distance to reference | `observed_zones`, `mtf_zone_map`, `lfx_mission_control.rows` |
| INV / Release | Depth imbalance, nearest bid/ask concentration, price dispersion | `monitoring_brief.now`, `lfx_mission_control.rows` |
| Confidence / Risk | Coverage, venue count, price dispersion, single-snapshot limitation | `monitoring_brief.confidence_risk`, `methodology`, `lfx_mission_control.rows` |

The same contract is exposed as structured JSON under:

```text
dashboard snapshot: lfx_alignment
dashboard snapshot: assets[].timeframes[].markets[].lfx_mission_control.rows
research_summary.json: lfx_alignment
research_summary.json: lfx_mission_control
```

## Practical-zone rules

- Render practical concentration and maximum-vacuum public-depth ranges instead of raw zone spam.
- Prefer M15 as the primary operating timeframe when the artifact profile declares it.
- Use M5, M15, and H1 as descriptive multi-timeframe context when present.
- Treat H4/D1 concepts as structural-only unless generated artifacts explicitly provide those timeframes.
- Use density or confluence wording as reference context only; it must not create a route, target, or signal.
- Use counterflow or route-origin wording as evidence-check text only; public artifacts do not prove private flow.
- Keep NEXT wording conditional and evidence-focused, not predictive.
- Use operating language and review checklists instead of trade-command language.

## Boundary

No BUY or SELL command. No entry, exit, stop-loss, take-profit, position sizing, asset ranking, prediction, automated execution, real market-maker inventory claim, real retail-positioning claim, hidden-liquidity claim, route or target creation, or future price-reaction claim.
