from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from crypto_composite.connectors.base import (
    ConnectorInputError,
    ExchangeConnector,
    parse_book_levels,
    require_non_empty_orderbook,
    require_timeframe,
)
from crypto_composite.schemas import OHLCVBar, OrderBookSnapshot, TradePrint
from crypto_composite.utils import now_ms, quote_volume

_INTERVAL = {"1m": "60", "5m": "300", "15m": "900", "1h": "3600"}


class CoinbaseConnector(ExchangeConnector):
    venue = "coinbase"
    base = "https://api.exchange.coinbase.com"

    def _require_spot(self, market_type: str) -> None:
        if market_type != "spot_usdt":
            raise ConnectorInputError(
                f"MARKET_TYPE_UNSUPPORTED venue={self.venue} market_type={market_type!r} supported=spot_usdt"
            )

    def _time_ms(self, value: Any) -> int:
        if isinstance(value, (int, float)):
            raw = float(value)
            return int(raw if raw >= 10_000_000_000 else raw * 1000)
        if isinstance(value, str):
            text = value.strip()
            try:
                if text.endswith("Z"):
                    dt = datetime.fromisoformat(text[:-1] + "+00:00")
                else:
                    dt = datetime.fromisoformat(text)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp() * 1000)
            except ValueError:
                return now_ms()
        return now_ms()

    def fetch_ohlcv(self, symbol, market_type, timeframe, limit):
        self._require_spot(market_type)
        granularity = require_timeframe(timeframe, _INTERVAL, venue=self.venue)
        data = self._get(f"{self.base}/products/{symbol}/candles", {"granularity": granularity})
        out = []
        for x in sorted(data, key=lambda item: int(item[0])):
            ts = self._time_ms(x[0])
            lo = float(x[1])
            hi = float(x[2])
            op = float(x[3])
            cl = float(x[4])
            vol = float(x[5])
            out.append(
                OHLCVBar(
                    self.venue,
                    market_type,
                    symbol,
                    timeframe,
                    ts,
                    op,
                    hi,
                    lo,
                    cl,
                    vol,
                    quote_volume(cl, vol),
                    None,
                    0.82,
                )
            )
        return out[-min(limit, 300) :] if limit > 0 else out

    def fetch_recent_trades(self, symbol, market_type, limit):
        self._require_spot(market_type)
        data = self._get(f"{self.base}/products/{symbol}/trades", {"limit": min(limit, 1000)})
        out = []
        for x in data:
            price = float(x["price"])
            qty = float(x["size"])
            maker_side = str(x.get("side", "")).lower()
            side = "sell" if maker_side == "buy" else "buy" if maker_side == "sell" else "unknown"
            out.append(
                TradePrint(
                    self.venue,
                    market_type,
                    symbol,
                    self._time_ms(x.get("time")),
                    price,
                    qty,
                    quote_volume(price, qty),
                    side,
                    True if side in ("buy", "sell") else None,
                    str(x.get("trade_id")) if x.get("trade_id") is not None else None,
                    0.78,
                )
            )
        return out

    def fetch_orderbook(self, symbol, market_type, depth):
        self._require_spot(market_type)
        data = self._get(f"{self.base}/products/{symbol}/book", {"level": 2})
        bids = parse_book_levels(data.get("bids", []))[:depth]
        asks = parse_book_levels(data.get("asks", []))[:depth]
        require_non_empty_orderbook(venue=self.venue, market_type=market_type, symbol=symbol, bids=bids, asks=asks)
        bb, ba = bids[0][0], asks[0][0]
        return OrderBookSnapshot(
            self.venue,
            market_type,
            symbol,
            self._time_ms(data.get("time")),
            bids,
            asks,
            bb,
            ba,
            (bb + ba) / 2,
            ba - bb,
            min(len(bids), len(asks)),
            0.78,
        )

    def fetch_funding(self, symbol, market_type):
        return None

    def fetch_open_interest(self, symbol, market_type):
        return None