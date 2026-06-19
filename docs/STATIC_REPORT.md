# Static HTML artifact report

`crypto-composite report` writes a self-contained HTML inspection page for generated JSON artifacts.

The report is designed for data-quality review, screenshots, GitHub Pages demos, and offline artifact sharing. It does not provide trading calls, execution instructions, position sizing, predictions, profitability claims, or financial advice.

## Usage

```bash
crypto-composite report \
  --artifact-root artifacts-universe \
  --out-file report.html
```

For a single-asset artifact folder:

```bash
crypto-composite report \
  --artifact-root artifacts \
  --out-file report.html
```

## What the report shows

- Overall artifact status.
- Overall quality score and A-F grade.
- Asset-level quality scores.
- Timeframe-level component scores.
- Venue coverage.
- Composite OHLCV coverage and status.
- Price dispersion score.
- Composite orderbook coverage and status.
- Validator warnings and errors.
- Links to JSON artifact files.

## Input files

The command reads the same artifact structures used by `validate-artifacts` and `score-artifacts`:

```text
universe_summary.json
run_summary.json
data_quality.json
composite_ohlcv.json
composite_orderbook_ladder.json
composite_ohlcv_<timeframe>.json
composite_orderbook_ladder_<timeframe>.json
```

If `quality_score.json` already exists, it can sit beside the report, but the report computes a fresh score from the artifact root so the HTML reflects current files.

## Output

```text
report.html
```

The HTML file is static and uses no JavaScript. It can be opened locally or copied into a static site workflow.

## Boundary

This report is data infrastructure. It is not a signal engine, strategy system, order system, or financial-advice document.
