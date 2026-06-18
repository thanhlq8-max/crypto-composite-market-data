from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

import requests

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


def require_timeframe(timeframe: str, mapping: Mapping[str, str], *, venue: str) -> str:
    """Return the exchange timeframe token or raise a domain-specific input error."""
    if timeframe not in mapping:
        supported = ",".join(sorted(mapping))
        raise UnsupportedTimeframeError(
            f"TIMEFRAME_UNSUPPORTED venue={venue} timeframe={timeframe!r} supported={supported}"
        )
    return mapping[timeframe]


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


class ExchangeConnector(ABC):
    venue: str
    timeout: int = 10

    def _get(self, url: str, params: dict | None = None):
        try:
            r = requests.get(url, params=params or {}, timeout=self.timeout)
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
