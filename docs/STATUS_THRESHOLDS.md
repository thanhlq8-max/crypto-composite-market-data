# Composite status thresholds

The composite engines label artifacts with a three-level status. The
thresholds below are **fixed heuristic gates**: they were chosen for the
default three-venue configuration and are not calibrated against measured
outage or divergence statistics. This page records their meaning; changing
any value is a scoped behavior change.

## OHLCV status (`composite_ohlcv.status_by_market_type`)

Judged on the **last closed bar** of each market type (`status_basis` in the
artifact notes records this):

| Status                  | Coverage        | Price dispersion |
|-------------------------|-----------------|------------------|
| `COMPOSITE_DATA_OK`     | >= 0.67         | <= 0.08 %        |
| `COMPOSITE_DATA_PARTIAL`| >= 0.34         | <= 0.20 %        |
| `COMPOSITE_DATA_WEAK`   | anything below either PARTIAL bound |

- **Coverage** = responding venues / venues capable of that market type
  (spot-only venues never count against perp coverage).
- **0.67** sits just above two thirds: with the three default venues, a
  2-of-3 bar (0.6667) is PARTIAL and only 3-of-3 reaches OK; with five spot
  venues, 4-of-5 (0.80) reaches OK. The intent is that OK requires more than
  a bare two-thirds majority of capable venues.
- **0.34** sits just above one third: a single venue out of three (0.3333)
  stays WEAK; OK/PARTIAL always require corroboration or better coverage.
- **Dispersion** = (max close − min close) / median close on the deciding
  bar, in percent. 0.08 % approximates the normal cross-venue spread band
  for liquid USDT majors; 0.20 % marks elevated-but-usable divergence.
  Larger values usually mean a stale or outlier venue feed.

## Orderbook ladder status (`composite_orderbook_ladder.status`)

Same coverage gates, no dispersion term:

| Status                   | Coverage |
|--------------------------|----------|
| `COMPOSITE_BOOK_OK`      | >= 0.67  |
| `COMPOSITE_BOOK_PARTIAL` | >= 0.34  |
| `COMPOSITE_BOOK_WEAK`    | < 0.34   |

## Boundaries

- Status describes **data corroboration only** — how many capable venues
  responded and how tightly their closes agree. It carries no market
  interpretation and no quality claim about any venue's matching engine.
- Implementations: `engines/composite_ohlcv.py` (`_status`) and
  `engines/composite_orderbook_ladder.py` (status block).
