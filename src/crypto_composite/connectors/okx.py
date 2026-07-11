from __future__ import annotations

from crypto_composite.connectors.base import (
    ExchangeConnector,
    UnsupportedTimeframeError,
    parse_book_levels,
    parse_records,
    require_non_empty_orderbook,
)

from crypto_composite.schemas import FundingSnapshot, OHLCVBar, OpenInterestSnapshot, OrderBookSnapshot, TradePrint
from crypto_composite.utils import quote_volume, now_ms

_BAR = {"1m":"1m", "5m":"5m", "15m":"15m", "1h":"1H"}

class OKXConnector(ExchangeConnector):
    venue = "okx"
    base = "https://www.okx.com"

    def _inst_type(self, market_type): return "SWAP" if market_type=="perp_usdt" else "SPOT"

    def fetch_ohlcv(self, symbol, market_type, timeframe, limit):
        if timeframe not in _BAR:
            supported = ",".join(sorted(_BAR))
            raise UnsupportedTimeframeError(f"TIMEFRAME_UNSUPPORTED venue={self.venue} timeframe={timeframe!r} supported={supported}")
        bar = _BAR[timeframe]
        data = self._get(self.base+"/api/v5/market/candles", {"instId":symbol,"bar":bar,"limit":limit}).get("data",[])
        def _bar_record(x):
            ts, op, hi, lo, cl, vol = int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])
            if min(op, hi, lo, cl) <= 0 or vol < 0:
                raise ValueError("invalid bar record")
            qv = float(x[7]) if len(x) > 7 and x[7] else quote_volume(cl, vol)
            return OHLCVBar(self.venue, market_type, symbol, timeframe, ts, op, hi, lo, cl, vol, qv, None, 0.9)
        return parse_records(list(reversed(data)), _bar_record)

    def fetch_recent_trades(self, symbol, market_type, limit):
        data = self._get(self.base+"/api/v5/market/trades", {"instId":symbol, "limit":min(limit,500)}).get("data",[])
        def _trade(x):
            price = float(x["px"])
            qty = float(x["sz"])
            side = x.get("side", "unknown")
            if price <= 0 or qty <= 0:
                raise ValueError("invalid trade record")
            return TradePrint(self.venue, market_type, symbol, int(x["ts"]), price, qty, quote_volume(price, qty), side, True if side in ("buy","sell") else None, x.get("tradeId"), 0.85)
        return parse_records(data, _trade)

    def fetch_orderbook(self, symbol, market_type, depth):
        items = self._get(self.base+"/api/v5/market/books", {"instId":symbol,"sz":min(depth,400)}).get("data",[])
        data = items[0] if items else {}
        bids = parse_book_levels(data.get("bids", []))
        asks = parse_book_levels(data.get("asks", []))
        require_non_empty_orderbook(venue=self.venue, market_type=market_type, symbol=symbol, bids=bids, asks=asks)
        bb,ba=bids[0][0], asks[0][0]
        return OrderBookSnapshot(self.venue, market_type, symbol, int(data.get("ts",now_ms())), bids, asks, bb, ba, (bb+ba)/2, ba-bb, min(len(bids),len(asks)), 0.85)

    def fetch_funding(self, symbol, market_type):
        if market_type != "perp_usdt":
            return None
        data = self._get(self.base+"/api/v5/public/funding-rate", {"instId":symbol}).get("data",[])
        if not data:
            return None
        x = data[0]
        return FundingSnapshot(self.venue, market_type, symbol, int(x.get("fundingTime",now_ms())), float(x.get("fundingRate",0)), int(x.get("nextFundingTime",0)) or None, 0.85)

    def fetch_open_interest(self, symbol, market_type):
        if market_type != "perp_usdt":
            return None
        data = self._get(self.base+"/api/v5/public/open-interest", {"instType":"SWAP","instId":symbol}).get("data",[])
        if not data:
            return None
        x = data[0]
        oi = float(x.get("oi", 0))
        return OpenInterestSnapshot(self.venue, market_type, symbol, int(x.get("ts",now_ms())), oi, None, 0.85)
