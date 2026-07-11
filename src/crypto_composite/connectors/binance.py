from __future__ import annotations

from crypto_composite.connectors.base import ExchangeConnector, parse_book_levels, parse_records, require_non_empty_orderbook, require_timeframe

from crypto_composite.connectors.base import ExchangeConnector, parse_book_levels, require_non_empty_orderbook, require_timeframe

from crypto_composite.schemas import FundingSnapshot, OHLCVBar, OpenInterestSnapshot, OrderBookSnapshot, TradePrint
from crypto_composite.utils import quote_volume, now_ms

_INTERVAL = {"1m":"1m", "5m":"5m", "15m":"15m", "1h":"1h"}

class BinanceConnector(ExchangeConnector):
    venue = "binance"

    def _base(self, market_type: str) -> str:
        return "https://fapi.binance.com" if market_type == "perp_usdt" else "https://api.binance.com"

    def fetch_ohlcv(self, symbol, market_type, timeframe, limit):
        path = "/fapi/v1/klines" if market_type == "perp_usdt" else "/api/v3/klines"
        interval = require_timeframe(timeframe, _INTERVAL, venue=self.venue)
        data = self._get(self._base(market_type)+path, {"symbol":symbol, "interval":interval, "limit":limit})
        def _bar(x):
            op,hi,lo,cl,vol = map(float, [x[1],x[2],x[3],x[4],x[5]])
            if min(op,hi,lo,cl) <= 0 or vol < 0: raise ValueError("invalid bar record")
            qv = float(x[7]) if len(x)>7 else quote_volume(cl, vol)
            tc = int(x[8]) if len(x)>8 else None
            return OHLCVBar(self.venue, market_type, symbol, timeframe, int(x[0]), op, hi, lo, cl, vol, qv, tc, 0.95)
        return parse_records(data, _bar)

    def fetch_recent_trades(self, symbol, market_type, limit):
        path = "/fapi/v1/aggTrades" if market_type == "perp_usdt" else "/api/v3/aggTrades"
        data = self._get(self._base(market_type)+path, {"symbol":symbol, "limit":min(limit,1000)})
        def _trade(x):
            price=float(x["p"]); qty=float(x["q"]); maker=bool(x.get("m", False))
            if price <= 0 or qty <= 0: raise ValueError("invalid trade record")
            # Binance m=True means buyer is maker => aggressive side is sell
            side = "sell" if maker else "buy"
            return TradePrint(self.venue, market_type, symbol, int(x["T"]), price, qty, quote_volume(price, qty), side, True, str(x.get("a")), 0.9)
        return parse_records(data, _trade)

    def fetch_orderbook(self, symbol, market_type, depth):
        path = "/fapi/v1/depth" if market_type == "perp_usdt" else "/api/v3/depth"
        data = self._get(self._base(market_type)+path, {"symbol":symbol, "limit":min(depth,1000)})
        bids = parse_book_levels(data.get("bids", []))
        asks = parse_book_levels(data.get("asks", []))
        require_non_empty_orderbook(venue=self.venue, market_type=market_type, symbol=symbol, bids=bids, asks=asks)
        bb,ba=bids[0][0], asks[0][0]
        return OrderBookSnapshot(self.venue, market_type, symbol, now_ms(), bids, asks, bb, ba, (bb+ba)/2, ba-bb, min(len(bids),len(asks)), 0.9)

    def fetch_funding(self, symbol, market_type):
        if market_type != "perp_usdt": return None
        data = self._get("https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol":symbol})
        return FundingSnapshot(self.venue, market_type, symbol, now_ms(), float(data.get("lastFundingRate",0.0)), int(data.get("nextFundingTime",0)) or None, 0.9)

    def fetch_open_interest(self, symbol, market_type):
        if market_type != "perp_usdt": return None
        data = self._get("https://fapi.binance.com/fapi/v1/openInterest", {"symbol":symbol})
        oi=float(data["openInterest"])
        return OpenInterestSnapshot(self.venue, market_type, symbol, now_ms(), oi, None, 0.9)
