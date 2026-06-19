# Artifact quality score

`crypto-composite score-artifacts` computes a compact, reproducible quality score from generated JSON artifacts.

This feature is data-infrastructure only. It does not produce trading signals, execution instructions, position sizing, financial advice, profitability claims, or market-maker intent claims.

## Score an artifact root

```bash
crypto-composite score-artifacts --artifact-root artifacts-universe
```

Write the score back into the artifact folder:

```bash
crypto-composite score-artifacts --artifact-root artifacts-universe --write
```

This creates:

```text
artifacts-universe/quality_score.json
```

## Output shape

```json
{
  "status": "OK",
  "mode": "universe",
  "quality_score": 91.4,
  "quality_grade": "A",
  "assets_checked": 3,
  "asset_scores": {},
  "errors": [],
  "warnings": [],
  "boundaries": [
    "Artifact quality scoring only; no trading signal, execution instruction, or financial advice."
  ]
}
```

## Scoring components

The score combines structural validation with public market-data quality fields already present in the artifacts:

- scan quality;
- scan status;
- venue coverage;
- composite OHLCV coverage;
- composite OHLCV status;
- latest price dispersion;
- composite orderbook coverage;
- composite orderbook status.

## Grades

```text
A  >= 90
B  >= 80
C  >= 65
D  >= 50
F  <  50
```

The score is intended to help downstream users decide whether artifacts are suitable for inspection or research. It is not an edge score, signal score, or prediction score.