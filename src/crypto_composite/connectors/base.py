from __future__ import annotations

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

    def __init__(self) -> None:
        self._session = build_retrying_session()

    def _get(self, url: str, params: dict | None = None):
        try:
            r = self._session.get(url, params=params or {}, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise ConnectorFetchError(f"{self.venue} fetch failed: {exc}") from exc

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
