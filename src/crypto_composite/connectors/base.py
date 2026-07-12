"""Shared plumbing for public exchange REST connectors.

The per-venue data_quality constants inside the concrete connectors are
heuristic ordering values, not measured accuracy; their basis and boundaries
are recorded in docs/DATA_QUALITY_CONSTANTS.md.
"""

from __future__ import annotations

import os
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from crypto_composite.schemas import (
    FundingSnapshot,
    OHLCVBar,
    OpenInterestSnapshot,
    OrderBookSnapshot,
    TradePrint,
)


class ConnectorFetchError(RuntimeError):
    pass


class ConnectorInputError(ValueError):
    pass


class UnsupportedTimeframeError(ConnectorInputError):
    pass


class ConnectorDataError(RuntimeError):
    pass


def parse_records(items: Sequence[Any] | None, parse_one: Callable[[Any], Any]) -> list[Any]:
    """Parse venue records one by one and skip records that fail to parse.

    One malformed public record (cast failure, missing field, non-positive
    price) must not discard the venue's whole market_type block.
    """
    out: list[Any] = []
    for item in items or []:
        try:
            out.append(parse_one(item))
        except (TypeError, ValueError, IndexError, KeyError):
            continue
    return out


def parse_book_levels(levels: Sequence[Any] | None) -> list[tuple[float, float]]:
    """Normalize exchange price/size levels and drop invalid public snapshot rows."""
    out: list[tuple[float, float]] = []
    for level in levels or []:
        try:
            price = float(level[0])
            size = float(level[1])
        except (TypeError, ValueError, IndexError):
            continue
        if price > 0 and size > 0:
            out.append((price, size))
    return out


def require_non_empty_orderbook(
    *,
    venue: str,
    market_type: str,
    symbol: str,
    bids: list[tuple[float, float]],
    asks: list[tuple[float, float]],
) -> None:
    if not bids or not asks:
        raise ConnectorDataError(
            f"EMPTY_ORDERBOOK venue={venue} market_type={market_type} symbol={symbol} "
            f"bids={len(bids)} asks={len(asks)}"
        )


RETRY_TOTAL = 3
RETRY_BACKOFF_SECONDS = 0.5
RETRY_STATUS_FORCELIST = (429, 500, 502, 503, 504)

# Conservative default budget per venue: far below every venue's public REST
# limit, and the burst covers a whole single-asset scan without sleeping.
DEFAULT_RATE_LIMIT_PER_SEC = 5.0
DEFAULT_RATE_LIMIT_BURST = 10.0
RATE_LIMIT_ENV_VAR = "CRYPTO_COMPOSITE_RATE_LIMIT_PER_SEC"
CACHE_TTL_ENV_VAR = "CRYPTO_COMPOSITE_CACHE_TTL_S"
_CACHE_MAX_ENTRIES = 512


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class TokenBucket:
    """Thread-safe token bucket. acquire() commits one token and returns the
    seconds the caller must sleep before proceeding (0.0 when within budget)."""

    def __init__(self, rate_per_sec: float, burst: float) -> None:
        self.rate = float(rate_per_sec)
        self.capacity = max(float(burst), 1.0)
        self._tokens = self.capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> float:
        if self.rate <= 0:
            return 0.0
        with self._lock:
            now = time.monotonic()
            self._tokens = min(self.capacity, self._tokens + (now - self._updated) * self.rate)
            self._updated = now
            self._tokens -= 1.0
            if self._tokens >= 0.0:
                return 0.0
            # Debt model: negative balance queues callers fairly.
            return -self._tokens / self.rate


_VENUE_BUCKETS: dict[str, TokenBucket] = {}
_BUCKETS_LOCK = threading.Lock()

_RESPONSE_CACHE: dict[tuple, tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()


def _venue_bucket(venue: str, rate_per_sec: float, burst: float) -> TokenBucket:
    with _BUCKETS_LOCK:
        bucket = _VENUE_BUCKETS.get(venue)
        if bucket is None:
            bucket = TokenBucket(rate_per_sec, burst)
            _VENUE_BUCKETS[venue] = bucket
        return bucket


def reset_rate_limiters() -> None:
    """Drop all venue buckets (test isolation / config change)."""
    with _BUCKETS_LOCK:
        _VENUE_BUCKETS.clear()


def _cache_get(key: tuple) -> Any | None:
    with _CACHE_LOCK:
        item = _RESPONSE_CACHE.get(key)
        if item is None:
            return None
        expires, payload = item
        if time.monotonic() >= expires:
            _RESPONSE_CACHE.pop(key, None)
            return None
        return payload


def _cache_put(key: tuple, payload: Any, ttl_s: float) -> None:
    with _CACHE_LOCK:
        if len(_RESPONSE_CACHE) >= _CACHE_MAX_ENTRIES:
            now = time.monotonic()
            for stale in [k for k, (expires, _) in _RESPONSE_CACHE.items() if expires <= now]:
                del _RESPONSE_CACHE[stale]
            while len(_RESPONSE_CACHE) >= _CACHE_MAX_ENTRIES:
                oldest = min(_RESPONSE_CACHE, key=lambda k: _RESPONSE_CACHE[k][0])
                del _RESPONSE_CACHE[oldest]
        _RESPONSE_CACHE[key] = (time.monotonic() + ttl_s, payload)


def clear_response_cache() -> None:
    """Drop all cached responses (test isolation / forced refresh)."""
    with _CACHE_LOCK:
        _RESPONSE_CACHE.clear()


def build_retrying_session() -> requests.Session:
    """Session with connection reuse and bounded GET retries for public endpoints."""
    session = requests.Session()
    retry = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF_SECONDS,
        status_forcelist=RETRY_STATUS_FORCELIST,
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class ExchangeConnector(ABC):
    venue: str
    timeout: int = 10
    # Per-venue request budget; env RATE_LIMIT_ENV_VAR overrides, 0 disables.
    rate_limit_per_sec: float = DEFAULT_RATE_LIMIT_PER_SEC
    rate_limit_burst: float = DEFAULT_RATE_LIMIT_BURST

    def __init__(self, cache_ttl_s: float | None = None) -> None:
        self._session = build_retrying_session()
        # Response caching is OPT-IN: a data-quality tool must not silently
        # serve stale market data. Enable per instance or via env for
        # repeated-scan loops (dashboard refresh, universe sweeps).
        self._cache_ttl_s = (
            float(cache_ttl_s) if cache_ttl_s is not None else _env_float(CACHE_TTL_ENV_VAR, 0.0)
        )

    def _get(self, url: str, params: dict | None = None):
        params = params or {}
        cache_key = (self.venue, url, tuple(sorted((str(k), str(v)) for k, v in params.items())))
        if self._cache_ttl_s > 0:
            cached = _cache_get(cache_key)
            if cached is not None:
                return cached
        rate = _env_float(RATE_LIMIT_ENV_VAR, self.rate_limit_per_sec)
        if rate > 0:
            wait = _venue_bucket(self.venue, rate, self.rate_limit_burst).acquire()
            if wait > 0:
                time.sleep(wait)
        try:
            r = self._session.get(url, params=params, timeout=self.timeout)
            r.raise_for_status()
            payload = r.json()
        except Exception as exc:
            raise ConnectorFetchError(f"{self.venue} fetch failed: {exc}") from exc
        if self._cache_ttl_s > 0:
            _cache_put(cache_key, payload, self._cache_ttl_s)
        return payload

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, market_type: str, timeframe: str, limit: int) -> list[OHLCVBar]: ...

    @abstractmethod
    def fetch_recent_trades(self, symbol: str, market_type: str, limit: int) -> list[TradePrint]: ...

    @abstractmethod
    def fetch_orderbook(self, symbol: str, market_type: str, depth: int) -> OrderBookSnapshot: ...

    @abstractmethod
    def fetch_funding(self, symbol: str, market_type: str) -> FundingSnapshot | None: ...

    @abstractmethod
    def fetch_open_interest(self, symbol: str, market_type: str) -> OpenInterestSnapshot | None: ...
