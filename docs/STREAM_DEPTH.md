# Depth-zone lifecycle streaming

REST snapshots can only proxy persistence: between two scans a depth wall may
have been present continuously or flickered in and out. `stream-depth`
watches the public perp book WebSocket streams for a bounded window and
records, per composite price bucket, how long depth was actually present.

## Install and run

```bash
pip install "crypto-composite-market-data[stream]"

crypto-composite stream-depth \
  --asset BTC-USDT \
  --venues binance,okx,bybit \
  --duration 120 \
  --out-dir artifacts
```

The command connects to the perp book streams (Binance USD-M partial depth
20 @ 500ms, OKX `books5`, Bybit `orderbook.50` with delta handling), derives
the reference price from the first cross-venue mid, and samples the merged
book once per `--sample-interval` (default 1s) into the same price-scaled
bucket grid the composite ladder uses. OKX sizes convert from contracts
through the instrument `ctVal`, exactly like the REST connector.

## Multi-asset and long runs

Stream several assets in parallel and (re)write partial artifacts on a fixed
cadence so a long run is not lost if interrupted:

```bash
crypto-composite stream-depth   --assets BTC-USDT,ETH-USDT,SOL-USDT   --duration 3600   --flush-interval 300   --out-dir artifacts
```

- One asset writes `zone_lifecycle.json` (unchanged). Multiple assets write
  `zone_lifecycle_{ASSET}.json` each.
- `--flush-interval N` rewrites every asset's artifact every N seconds during
  the run; without it artifacts are written once at the end.
- Long-run memory is bounded per asset: buckets absent longer than 10 minutes
  are dropped, and the total bucket count is capped (oldest currently-absent
  dropped first). Pruning is recorded in the artifact `notes`; a pruned bucket
  that reappears is counted fresh.

## Output

`zone_lifecycle.json` (see `ARTIFACT_SCHEMA.md`): per bucket the first/last
sighting, accumulated `observed_ms`, `uptime_ratio` over the window,
`refill_count` (disappear-then-reappear transitions), depth peaks/averages,
and the maximum number of venues that corroborated the bucket in one sample.

Reading it:

- `uptime_ratio` near 1 with `refill_count` 0 — depth stayed put for the
  whole window.
- high `refill_count` — the bucket flickered; snapshot-based persistence
  would have overstated it.
- `max_venue_count` >= 2 — more than one venue held depth in the bucket at
  the same moment.

## Limits and boundaries

- Venue streams carry top-of-book levels only (20/5/50 levels), so lifecycle
  buckets describe the near-book area visible in the streams — not the full
  +/-2.5% REST ladder band.
- Reconnects use bounded backoff (5 attempts per venue) and are recorded in
  `notes`; a silent venue is listed rather than failing the run.
- Observed public data only: no trading signal, prediction, execution
  instruction, hidden-liquidity or market-maker-intent claim.
