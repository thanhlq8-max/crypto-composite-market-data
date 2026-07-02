# Static research dataset report

`crypto-composite research-report` writes a static HTML research report and a machine-readable JSON summary from an existing artifact root.

The command is designed for public demo artifacts, reproducible research intake, notebook handoff, and quick review of generated multi-exchange market-data datasets. It does not fetch live exchange data and does not create asset rankings, trading signals, predictions, execution instructions, profitability claims, or financial advice.

## Usage

```bash
crypto-composite research-report \
  --artifact-root artifacts-universe \
  --out-file research_report.html \
  --summary-file research_summary.json
```

For the checked-in synthetic sample:

```bash
crypto-composite research-report \
  --artifact-root examples/sample_artifacts \
  --out-file sample-report/research_report.html \
  --summary-file sample-report/research_summary.json
```

## What the report shows

- Dataset scope: assets, timeframes, market types, primary timeframe, refresh metadata, and JSON artifact count.
- Quality gate: current validator and artifact quality status.
- LFX-2 alignment contract: monitor-only MM Mission / TRADER Mode / NEXT Scenario / DID / DOING / KEY Zones / INV-Release / Confidence-Risk mapping to artifact fields.
- LFX mission-control artifact readout: one object-list row per display panel, asset, timeframe, and market type.
- Market microstructure metrics: latest composite close, venue count, OHLCV coverage, price dispersion, public orderbook coverage, bid/ask depth totals, and depth imbalance.
- Observed zone evidence: corroborated, concentrated, and limited public-depth bucket counts plus nearest bid/ask concentration ranges and `lfx_zone_review` role/value objects.
- Public demo artifacts: links to the source JSON files behind the report.
- Caveats: single-snapshot and public-data-only limitations.

## Output files

```text
research_report.html
research_summary.json
```

`research_summary.json` is intended for downstream notebooks, static-site checks, and reproducible review. It keeps artifact rows as object lists rather than prose-only blobs.

The JSON summary includes `lfx_alignment` so downstream users can verify which LFX-2 monitor-only display contract is being applied. It also includes `lfx_mission_control` as a flat object list for notebooks, static-site checks, and public demos. Observed zones keep nested `lfx_zone_review` objects so downstream readers can inspect zone role, density-reference context, and refresh checks without parsing prose.

## Input files

The command reads the same artifact structures used by `validate-artifacts`, `score-artifacts`, and the dashboard snapshot builder:

```text
universe_summary.json
run_summary.json
data_quality.json
composite_ohlcv.json
composite_orderbook_ladder.json
dashboard_profile.json
```

## Boundary

Observed zones are public orderbook bucket diagnostics. They do not prove support/resistance, hidden liquidity, market-maker intent, or future price reaction.

The report is a research dataset artifact. It is not a signal engine, prediction system, strategy system, order system, or financial-advice document.
