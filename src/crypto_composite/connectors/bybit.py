from __future__ import annotations
from crypto_composite.connectors.base import ExchangeConnector, parse_book_levels, parse_records, require_non_empty_orderbook, require_timeframe
from crypto_composite.schemas import FundingSnapshot, OHLCVBar, OpenInterestSnapshot, OrderBookSnapshot, TradePrint
from crypto_composite.utils import quote_volume, now_ms

_INTERVAL = {"1m":"1", "5m":"5", "15m":"15", "1h":"60"}

class BybitConnector(ExchangeConnector):
    venue = "bybit"
    base = "https://api.bybit.com"

    def _cat(self, market_type): return "linear" if market_type=="perp_usdt" else "spot"

    def fetch_ohlcv(self, symbol, market_type, timeframe, limit):
        interval = require_timeframe(timeframe, _INTERVAL, venue=self.venue)
        data=self._get(self.base+"/v5/market/kline", {"category":self._cat(market_type),"symbol":symbol,"interval":interval,"limit":limit}).get("result",{}).get("list",[])
        def _bar(x):
            ts,op,hi,lo,cl,vol = int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])
            if min(op,hi,lo,cl) <= 0 or vol < 0: raise ValueError("invalid bar record")
            qv = float(x[6]) if len(x)>6 else quote_volume(cl, vol)
            return OHLCVBar(self.venue, market_type, symbol, timeframe, ts, op, hi, lo, cl, vol, qv, None, 0.85)
        return parse_records(list(reversed(data)), _bar)

    def fetch_recent_trades(self, symbol, market_type, limit):
        data=self._get(self.base+"/v5/market/recent-trade", {"category":self._cat(market_type),"symbol":symbol,"limit":min(limit,1000)}).get("result",{}).get("list",[])
        def _trade(x):
            price=float(x["price"]); qty=float(x["size"]); side=x.get("side","").lower() or "unknown"
            if price <= 0 or qty <= 0: raise ValueError("invalid trade record")
            return TradePrint(self.venue, market_type, symbol, int(x.get("time", now_ms())), price, qty, quote_volume(price, qty), side, True if side in ("buy","sell") else None, x.get("execId"), 0.8)
        return parse_records(data, _trade)

    def fetch_orderbook(self, symbol, market_type, depth):
        data=self._get(self.base+"/v5/market/orderbook", {"category":self._cat(market_type),"symbol":symbol,"limit":min(depth,500)}).get("result",{})
        bids = parse_book_levels(data.get("b", []))
        asks = parse_book_levels(data.get("a", []))
        require_non_empty_orderbook(venue=self.venue, market_type=market_type, symbol=symbol, bids=bids, asks=asks)
        bb,ba=bids[0][0], asks[0][0]
        return OrderBookSnapshot(self.venue, market_type, symbol, int(data.get("ts",now_ms())), bids, asks, bb, ba, (bb+ba)/2, ba-bb, min(len(bids),len(asks)), 0.8)

    def fetch_funding(self, symbol, market_type):
        if market_type!="perp_usdt": return None
        data=self._get(self.base+"/v5/market/funding/history", {"category":"linear","symbol":symbol,"limit":1}).get("result",{}).get("list",[])
        if not data: return None
        x=data[0]
        return FundingSnapshot(self.venue, market_type, symbol, int(x.get("fundingRateTimestamp", now_ms())), float(x.get("fundingRate",0)), None, 0.8)

    def fetch_open_interest(self, symbol, market_type):
        if market_type!="perp_usdt": return None
        data=self._get(self.base+"/v5/market/open-interest", {"category":"linear","symbol":symbol,"intervalTime":"5min","limit":1}).get("result",{}).get("list",[])
        if not data: return None
        x=data[0]; oi=float(x.get("openInterest",0))
        return OpenInterestSnapshot(self.venue, market_type, symbol, int(x.get("timestamp",now_ms())), oi, None, 0.8)
