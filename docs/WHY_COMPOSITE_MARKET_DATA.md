# Why composite public market data

One public exchange feed answers what that venue reported. It does not show whether other venues were available, aligned, or materially different at the same timestamp.

`crypto-composite-market-data` keeps the source records and adds explicit cross-venue context. The goal is to help downstream systems decide whether an artifact is sufficiently covered and internally consistent for inspection. It is not a trading-signal or execution system.

## Three questions a composite can answer

1. **Coverage:** how many expected venues contributed usable records?
2. **Dispersion:** how far apart were the venue closing prices at the aligned timestamp?
3. **Concentration:** how much of a public orderbook bucket came from one venue rather than the venue set?

These are data-quality questions. They do not establish fair value, future direction, hidden liquidity, or profitability.

## Venue coverage

For each aligned OHLCV timestamp, coverage is:

```text
coverage = contributing venue count / expected venue count
```

The value is clamped to the range `0.0` to `1.0`. The expected venue set comes from the requested run, while the contributing count is based on normalized records present at that timestamp.

Coverage is interpreted by the current OHLCV status contract together with price dispersion:

| Status | Coverage requirement | Latest dispersion requirement |
|---|---:|---:|
| `COMPOSITE_DATA_OK` | at least `0.67` | at most `0.08%` |
| `COMPOSITE_DATA_PARTIAL` | at least `0.34` | at most `0.20%` |
| `COMPOSITE_DATA_WEAK` | otherwise | otherwise |

For composite orderbooks, the current status contract uses coverage alone:

| Status | Coverage requirement |
|---|---:|
| `COMPOSITE_BOOK_OK` | at least `0.67` |
| `COMPOSITE_BOOK_PARTIAL` | at least `0.34` |
| `COMPOSITE_BOOK_WEAK` | otherwise |

Coverage measures record presence after connector parsing. It does not prove that a venue is correct, complete, or representative.

## Price dispersion

For aligned closes from more than one venue, the implementation calculates:

```text
price_dispersion_pct = (maximum close - minimum close) / median close * 100
```

The median close remains in the artifact alongside the quote-volume-weighted close. This makes the cross-venue range inspectable without replacing it with one opaque aggregate.

A higher dispersion value means the aligned venue closes disagree more. Possible causes include timing boundaries, stale or missing source updates, exchange-specific market structure, or a connector/data issue. The metric does not identify which cause is true.

## OHLCV composition

Source bars are grouped by market type and timestamp before aggregation. For each aligned group, the artifact records:

| Field | Current calculation |
|---|---|
| `open` | quote-volume-weighted source opens |
| `high` | maximum source high |
| `low` | minimum source low |
| `close` / `vwap_close` | quote-volume-weighted source closes |
| `median_close` | median source close |
| `volume_base_total` | sum of source base volumes |
| `volume_quote_total` | sum of source quote volumes |
| `venue_weights` | each venue's share of quote volume |
| `coverage` | contributing venues divided by expected venues |
| `price_dispersion_pct` | cross-venue close range divided by median close |

Keeping these fields separate lets a downstream consumer inspect how the composite was formed instead of treating the output as a single unexplained price series.

## Public orderbook concentration

The orderbook ladder groups valid public bid and ask levels into price buckets near a reference price. Within each bucket, quote depth is retained by venue in `venue_depth_quote`.

Concentration is summarized with the Herfindahl-Hirschman Index (HHI):

```text
hhi = sum((venue depth / total bucket depth) ** 2)
```

If one venue supplies all bucket depth, HHI is `1.0`. If three venues supply equal depth, HHI is approximately `0.333`. HHI describes public depth concentration in that snapshot; it does not reveal hidden orders or matching-engine intent.

The ladder also exposes depth totals, coverage, depth imbalance, persistence, `spoof_risk_proxy`, and `vacuum_score`. Persistence, `spoof_risk_proxy`, and `vacuum_score` are bounded public-data heuristics. They must not be described as proof of spoofing, future price movement, or executable liquidity.

## Checked-in synthetic example

The fixture at [`examples/sample_artifacts/BTC-USDT`](../examples/sample_artifacts/BTC-USDT) is deterministic and explicitly non-live. Its `15m` spot composite records:

- expected venues: Binance, OKX, and Bybit;
- contributing venue count: `3`;
- coverage: `1.0`;
- median and volume-weighted close: `101.0`;
- price dispersion: `0.04%`;
- data quality: `0.95`; and
- status: `COMPOSITE_DATA_OK`.

Those values demonstrate the artifact contract only. They are not observations about a real market period.

## Downstream inspection checklist

Before consuming a composite artifact:

1. Read `data_quality.json` for failed venues and missing sources.
2. Confirm the expected venue set matches the intended run.
3. Inspect coverage at the timestamps the downstream workflow uses.
4. Review `price_dispersion_pct` instead of relying only on the composite close.
5. Inspect `venue_weights` or `venue_depth_quote` for single-venue concentration.
6. Preserve the artifact's market type and timeframe boundaries.
7. Treat weak or partial status as an explicit limitation, not as a directional signal.

See [Artifact schema](ARTIFACT_SCHEMA.md), [Data quality model](DATA_QUALITY.md), and [Consume artifacts safely](TUTORIAL_CONSUME_ARTIFACTS.md) for the corresponding file contracts and offline example.

## Boundary

Composite public market data improves observability of source coverage and disagreement. It does not provide private orderflow, account data, order execution, asset rankings, entry or exit instructions, or financial advice.
