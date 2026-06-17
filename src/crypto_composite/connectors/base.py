from __future__ import annotations
import requests
from abc import ABC, abstractmethod
from crypto_composite.schemas import OHLCVBar, TradePrint, OrderBookSnapshot, FundingSnapshot, OpenInterestSnapshot

class ConnectorFetchError(RuntimeError):
    pass

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
