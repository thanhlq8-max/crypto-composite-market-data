# Per-venue rate limiting and response cache

## Rate limiting (on by default)

Every connector request passes through a token bucket shared by all connector
instances of the same venue in the process:

- Default budget: **5 requests/second per venue** with a **burst of 10** — far
  below every venue's public REST limit, and the burst covers a full
  single-asset scan without sleeping. Multi-asset universe runs are smoothed
  automatically because the bucket is shared across connector instances.
- Override per process with the environment variable
  `CRYPTO_COMPOSITE_RATE_LIMIT_PER_SEC` (a float; `0` disables limiting).
- Override per connector subclass with the `rate_limit_per_sec` /
  `rate_limit_burst` class attributes.

The limiter spaces requests *before* they are sent; the retry layer
(429-aware, GET-only) remains the backstop if a venue still throttles.

## Response cache (opt-in, off by default)

A data-quality tool must not silently serve stale market data, so caching is
disabled unless explicitly enabled:

- Per process: set `CRYPTO_COMPOSITE_CACHE_TTL_S` (seconds, e.g. `5`).
- Per connector instance: `BinanceConnector(cache_ttl_s=5.0)`.

When enabled, identical GET requests (same venue, URL, and parameters) within
the TTL return the cached JSON payload without a network call. The cache is
process-wide, capped at 512 entries (expired entries are evicted first), and
keyed by exact parameters — different symbols, timeframes, or depths never
share entries.

Intended use: repeated-scan loops such as dashboard refresh cycles or
universe sweeps that re-read slow-moving endpoints within a few seconds.
Artifacts record whatever payload was used; enabling the cache trades
freshness for request volume and should be reflected in how often you run
scans.

## Boundaries

- Both features shape request volume only; they add no new data sources and
  no trading semantics.
- Cached payloads are returned by reference and must not be mutated by
  callers (package parsers never mutate them).
