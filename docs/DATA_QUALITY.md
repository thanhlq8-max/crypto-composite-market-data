# Data quality model

The project reports two distinct quality layers.

## Source scan quality

`DataQualityReport` summarizes venue availability and normalized record quality:

- `venues_requested`
- `venues_ok`
- `venues_failed`
- `missing_sources`
- `overall_quality`
- `status`

Source status values:

```text
OK
PARTIAL
INSUFFICIENT_DATA
```

## Composite OHLCV status

Composite OHLCV status is based on venue coverage and latest timestamp price dispersion:

```text
COMPOSITE_DATA_OK
COMPOSITE_DATA_PARTIAL
COMPOSITE_DATA_WEAK
```

A weak label means the artifact should be treated as incomplete market-data context, not as a reliable composite state.

## Composite orderbook status

Composite orderbook ladder status is based on venue coverage:

```text
COMPOSITE_BOOK_OK
COMPOSITE_BOOK_PARTIAL
COMPOSITE_BOOK_WEAK
```

The ladder is a public snapshot proxy. It cannot prove hidden liquidity, private orderflow, or exchange matching-engine intent.
