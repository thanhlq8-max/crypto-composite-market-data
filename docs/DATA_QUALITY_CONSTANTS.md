# Per-venue data_quality constants

Every record a connector emits carries a `data_quality` value between 0 and 1.
These values are **hand-set heuristic ordering constants**, fixed at project
start. They are **not** measured error rates, uptime statistics, or calibrated
accuracy scores, and no external documentation backs the specific numbers.
This page is the traceability label required for artifact-exported numbers.

## Current values

| Venue    | OHLCV | Trades | Orderbook | Funding | Open interest |
|----------|-------|--------|-----------|---------|---------------|
| binance  | 0.95  | 0.90   | 0.90      | 0.90    | 0.90          |
| okx      | 0.90  | 0.85   | 0.85      | 0.85    | 0.85          |
| bybit    | 0.85  | 0.80   | 0.80      | 0.80    | 0.80          |
| coinbase | 0.82  | 0.78   | 0.78      | n/a     | n/a           |
| kraken   | 0.82  | 0.78   | 0.78      | n/a     | n/a           |

Constants are inline literals in `src/crypto_composite/connectors/{binance,okx,bybit,coinbase,kraken}.py`.

## What the ordering encodes

The relative ordering (not the absolute magnitudes) reflects how much of the
artifact schema each venue's public payload fills natively versus how much the
connector has to derive:

- **binance** returns quote volume, trade counts, and aggressor flags natively
  in the same payload, at millisecond timestamps.
- **okx** returns quote volume for candles and explicit trade sides; open
  interest and funding arrive as separate single-record endpoints.
- **bybit** returns quote-ish `turnover` for candles; trade timestamps are
  per-record but funding history needs a separate paginated endpoint.
- **coinbase / kraken** (spot only) need derived quote volume
  (`close x base_volume`), timestamp conversion (ISO strings / epoch seconds),
  and provide no perp surface at all.

Within one venue, OHLCV is rated slightly above trades/orderbook because
candles are consolidated by the exchange while trades/book snapshots are
point-in-time reads that the composite layer must reconcile.

## How the values flow downstream

- `composite_ohlcv.build_composite_ohlcv` averages per-record `data_quality`
  per timestamp bucket, scales by coverage, and subtracts a dispersion
  penalty. The constants therefore act as venue weighting priors, and small
  differences (0.78 vs 0.95) shift composite `data_quality` by at most that
  same order of magnitude.
- `engines.scan` averages all record qualities into
  `quality_report.overall_quality`, which feeds the scan `status` gate.

## Boundaries

- Changing any value is a behavior change (composite weights shift) and needs
  its own scoped change with regression evidence; this document only records
  the basis. See PROJECT decision history (B5).
- The constants make no claim about venue trustworthiness, execution quality,
  or market behavior; they describe public payload surface only.
