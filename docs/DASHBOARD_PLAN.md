# Local dashboard plan

The dashboard should visualize artifact quality and public market-data structure. It should not become a trading terminal.

## Implemented architecture

```text
Python stdlib ThreadingHTTPServer
|-- safe artifact reader
|-- JSON API endpoints
`-- same-origin static frontend
```

Dashboard V2 covers composite price context, public depth, practical observed zones, source corroboration, spot/perpetual dislocation, artifact paths, and read-only JSON inspection. Future panels must continue to use the existing public artifact contract and wording guard.

## Implemented analytical endpoint

```text
/api/dashboard-snapshot
```

The endpoint joins existing combined OHLCV, orderbook ladder, quality, run-summary, and universe-summary artifacts. It does not mutate artifacts or pipeline behavior.

## Dashboard V2 panels

1. Asset/timeframe/market filters and current composite metrics.
2. Past observation, current observation, and next evidence check.
3. Composite close chart with observed zone bands.
4. Public-depth profile.
5. Practical observed-zone table with evidence grades.
6. Spot/perpetual dislocation context.
7. Methodology and artifact manifest.

The layout adapts the LFX-2 readability principles of time-layered context, practical-zone filtering, conditional monitoring, and explicit confidence/risk. Trading-specific MM, retail-positioning, route, entry, and prediction semantics are intentionally excluded.

## Wording guard

Use data-quality language:

- OK / partial / weak.
- Coverage.
- Dispersion.
- Public depth.
- Artifact generated / missing.

Do not use trading language:

- Buy / sell.
- Long / short now.
- Entry.
- Stop-loss / take-profit.
- Signal confidence.
