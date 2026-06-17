from __future__ import annotations
from crypto_composite.connectors.base import ExchangeConnector
from crypto_composite.schemas import *
from crypto_composite.utils import quote_volume, now_ms

_INTERVAL = {"1m":"1m", "5m":"5m", "15m":"15m", "1h":"1h"}

class BinanceConnector(ExchangeConnector):
    venue = "binance"

    def _base(self, market_type: str) -> str:
        return "https://fapi.binance.com" if market_type == "perp_usdt" else "https://api.binance.com"

    def fetch_ohlcv(self, symbol, market_type, timeframe, limit):
        path = "/fapi/v1/klines" if market_type == "perp_usdt" else "/api/v3/klines"
        data = self._get(self._base(market_type)+path, {"symbol":symbol, "interval":_INTERVAL[timeframe], "limit":limit})
        out=[]
        for x in data:
            op,hi,lo,cl,vol = map(float, [x[1],x[2],x[3],x[4],x[5]])
            qv = float(x[7]) if len(x)>7 else quote_volume(cl, vol)
            tc = int(x[8]) if len(x)>8 else None
            out.append(OHLCVBar(self.venue, market_type, symbol, timeframe, int(x[0]), op, hi, lo, cl, vol, qv, tc, 0.95))
        return out

    def fetch_recent_trades(self, symbol, market_type, limit):
        path = "/fapi/v1/aggTrades" if market_type == "perp_usdt" else "/api/v3/aggTrades"
        data = self._get(self._base(market_type)+path, {"symbol":symbol, "limit":min(limit,1000)})
        out=[]
        for x in data:
            price=float(x["p"]); qty=float(x["q"]); maker=bool(x.get("m", False))
            # Binance m=True means buyer is maker => aggressive side is sell
            side = "sell" if maker else "buy"
            out.append(TradePrint(self.venue, market_type, symbol, int(x["T"]), price, qty, quote_volume(price, qty), side, True, str(x.get("a")), 0.9))
        return out

    def fetch_orderbook(self, symbol, market_type, depth):
        path = "/fapi/v1/depth" if market_type == "perp_usdt" else "/api/v3/depth"
        data = self._get(self._base(market_type)+path, {"symbol":symbol, "limit":min(depth,1000)})
        bids=[(float(p),float(q)) for p,q in data["bids"]]
        asks=[(float(p),float(q)) for p,q in data["asks"]]
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
