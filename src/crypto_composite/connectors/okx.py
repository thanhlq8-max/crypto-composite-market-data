from __future__ import annotations

from crypto_composite.connectors.base import (
    ConnectorDataError,
    ExchangeConnector,
    UnsupportedTimeframeError,
    parse_book_levels,
    parse_records,
    require_non_empty_orderbook,
)

from crypto_composite.schemas import FundingSnapshot, OHLCVBar, OpenInterestSnapshot, OrderBookSnapshot, TradePrint
from crypto_composite.utils import quote_volume, now_ms

# OKX anchors plain 1D candles to Hong Kong time (UTC+8); the utc-suffixed bar
# keeps daily bar opens aligned with the other venues' UTC midnight anchor.
# 4H boundaries coincide for both anchors (+8h is a multiple of 4h).
_BAR = {"1m":"1m", "5m":"5m", "15m":"15m", "1h":"1H", "4h":"4H", "1d":"1Dutc"}

# ctVal per SWAP instrument (e.g. BTC-USDT-SWAP -> 0.01 BTC). OKX derivative
# endpoints report candle vol, trade sz, book sz, and oi in CONTRACTS, not
# base currency (live-verified 2026-07-12: vol/volCcy ratio exactly 1/ctVal).
_CT_VAL_CACHE: dict[str, float] = {}


class OKXConnector(ExchangeConnector):
    venue = "okx"
    base = "https://www.okx.com"

    def _inst_type(self, market_type): return "SWAP" if market_type=="perp_usdt" else "SPOT"

    def _data(self, payload):
        """Unwrap the OKX envelope; business errors arrive as HTTP 200 + code."""
        code = str(payload.get("code", "0"))
        if code != "0":
            raise ConnectorDataError(
                f"OKX_API_ERROR venue={self.venue} code={code} msg={payload.get('msg', '')!r}"
            )
        return payload.get("data", [])

    def _contract_value(self, symbol):
        """Base-currency value of one contract for a SWAP instrument, cached."""
        ct_val = _CT_VAL_CACHE.get(symbol)
        if ct_val is None:
            data = self._data(self._get(
                self.base+"/api/v5/public/instruments", {"instType": "SWAP", "instId": symbol}
            ))
            if not data:
                raise ConnectorDataError(f"OKX_INSTRUMENT_MISSING venue={self.venue} instId={symbol}")
            ct_val = float(data[0].get("ctVal", 0))
            if ct_val <= 0:
                raise ConnectorDataError(f"OKX_CT_VAL_INVALID venue={self.venue} instId={symbol}")
            _CT_VAL_CACHE[symbol] = ct_val
        return ct_val

    def fetch_ohlcv(self, symbol, market_type, timeframe, limit):
        if timeframe not in _BAR:
            supported = ",".join(sorted(_BAR))
            raise UnsupportedTimeframeError(f"TIMEFRAME_UNSUPPORTED venue={self.venue} timeframe={timeframe!r} supported={supported}")
        bar = _BAR[timeframe]
        data = self._data(self._get(self.base+"/api/v5/market/candles", {"instId":symbol,"bar":bar,"limit":min(limit, 300)}))
        perp = market_type == "perp_usdt"
        ct_val = self._contract_value(symbol) if perp else None
        def _bar_record(x):
            ts, op, hi, lo, cl = int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4])
            if perp:
                # Candle columns: [ts,o,h,l,c,vol(contracts),volCcy(base),volCcyQuote,...]
                vol = float(x[6]) if len(x) > 6 and x[6] else float(x[5]) * ct_val
            else:
                vol = float(x[5])
            if min(op, hi, lo, cl) <= 0 or vol < 0:
                raise ValueError("invalid bar record")
            qv = float(x[7]) if len(x) > 7 and x[7] else quote_volume(cl, vol)
            return OHLCVBar(self.venue, market_type, symbol, timeframe, ts, op, hi, lo, cl, vol, qv, None, 0.9)
        return parse_records(list(reversed(data)), _bar_record)

    def fetch_recent_trades(self, symbol, market_type, limit):
        data = self._data(self._get(self.base+"/api/v5/market/trades", {"instId":symbol, "limit":min(limit,500)}))
        contract_value = self._contract_value(symbol) if market_type == "perp_usdt" else 1.0
        def _trade(x):
            price = float(x["px"])
            qty = float(x["sz"]) * contract_value
            side = x.get("side", "unknown")
            if price <= 0 or qty <= 0:
                raise ValueError("invalid trade record")
            return TradePrint(self.venue, market_type, symbol, int(x["ts"]), price, qty, quote_volume(price, qty), side, True if side in ("buy","sell") else None, x.get("tradeId"), 0.85)
        return parse_records(data, _trade)

    def fetch_orderbook(self, symbol, market_type, depth):
        items = self._data(self._get(self.base+"/api/v5/market/books", {"instId":symbol,"sz":min(depth,400)}))
        data = items[0] if items else {}
        bids = parse_book_levels(data.get("bids", []))
        asks = parse_book_levels(data.get("asks", []))
        if market_type == "perp_usdt":
            # Book sizes arrive in contracts for SWAP instruments.
            contract_value = self._contract_value(symbol)
            bids = [(price, size * contract_value) for price, size in bids]
            asks = [(price, size * contract_value) for price, size in asks]
        require_non_empty_orderbook(venue=self.venue, market_type=market_type, symbol=symbol, bids=bids, asks=asks)
        bb,ba=bids[0][0], asks[0][0]
        return OrderBookSnapshot(self.venue, market_type, symbol, int(data.get("ts",now_ms())), bids, asks, bb, ba, (bb+ba)/2, ba-bb, min(len(bids),len(asks)), 0.85)

    def fetch_funding(self, symbol, market_type):
        if market_type != "perp_usdt":
            return None
        data = self._data(self._get(self.base+"/api/v5/public/funding-rate", {"instId":symbol}))
        if not data:
            return None
        x = data[0]
        return FundingSnapshot(self.venue, market_type, symbol, int(x.get("fundingTime",now_ms())), float(x.get("fundingRate",0)), int(x.get("nextFundingTime",0)) or None, 0.85)

    def fetch_open_interest(self, symbol, market_type):
        if market_type != "perp_usdt":
            return None
        data = self._data(self._get(self.base+"/api/v5/public/open-interest", {"instType":"SWAP","instId":symbol}))
        if not data:
            return None
        x = data[0]
        # oiCcy is base currency; oi is a contract count for SWAP instruments.
        oi_ccy = x.get("oiCcy")
        if oi_ccy:
            oi = float(oi_ccy)
        else:
            oi = float(x.get("oi", 0)) * self._contract_value(symbol)
        return OpenInterestSnapshot(self.venue, market_type, symbol, int(x.get("ts",now_ms())), oi, None, 0.85)
