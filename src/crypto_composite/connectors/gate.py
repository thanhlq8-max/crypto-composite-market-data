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
from crypto_composite.utils import now_ms, quote_volume

# Gate.io intervals share one token set across spot and USDT futures.
_INTERVAL = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}

# quanto_multiplier per USDT-settled contract (e.g. BTC_USDT -> 0.0001 BTC).
# Gate.io futures endpoints report candle volume, trade size, book size, and
# open interest in CONTRACTS (live-verified 2026-07-12), so perp sizes must be
# scaled to base currency exactly like OKX SWAP.
_MULTIPLIER_CACHE: dict[str, float] = {}


class GateConnector(ExchangeConnector):
    venue = "gate"
    base = "https://api.gateio.ws/api/v4"

    def _time_ms(self, value) -> int:
        try:
            raw = float(value)
        except (TypeError, ValueError):
            return now_ms()
        # Gate mixes second and millisecond epochs across endpoints.
        return int(raw if raw >= 10_000_000_000 else raw * 1000)

    def _require_timeframe(self, timeframe: str) -> str:
        if timeframe not in _INTERVAL:
            supported = ",".join(sorted(_INTERVAL))
            raise UnsupportedTimeframeError(
                f"TIMEFRAME_UNSUPPORTED venue={self.venue} timeframe={timeframe!r} supported={supported}"
            )
        return _INTERVAL[timeframe]

    def _multiplier(self, symbol: str) -> float:
        """Base-currency value of one futures contract, cached per symbol."""
        mult = _MULTIPLIER_CACHE.get(symbol)
        if mult is None:
            data = self._get(f"{self.base}/futures/usdt/contracts/{symbol}")
            mult = float(data.get("quanto_multiplier", 0) or 0)
            if mult <= 0:
                raise ConnectorDataError(f"GATE_MULTIPLIER_INVALID venue={self.venue} contract={symbol}")
            _MULTIPLIER_CACHE[symbol] = mult
        return mult

    # -- spot -----------------------------------------------------------------

    def _fetch_spot_ohlcv(self, symbol, timeframe, limit):
        interval = self._require_timeframe(timeframe)
        data = self._get(
            f"{self.base}/spot/candlesticks",
            {"currency_pair": symbol, "interval": interval, "limit": min(limit, 1000)},
        )

        def _bar(x):
            # [ts_s, quote_volume, close, high, low, open, base_volume, closed]
            ts = self._time_ms(x[0])
            cl, hi, lo, op = float(x[2]), float(x[3]), float(x[4]), float(x[5])
            base_vol = float(x[6]) if len(x) > 6 else 0.0
            quote_vol = float(x[1])
            if min(op, hi, lo, cl) <= 0 or base_vol < 0:
                raise ValueError("invalid bar record")
            return OHLCVBar(self.venue, "spot_usdt", symbol, timeframe, ts, op, hi, lo, cl, base_vol, quote_vol, None, 0.8)

        return parse_records(data, _bar)

    def _fetch_spot_trades(self, symbol, limit):
        data = self._get(f"{self.base}/spot/trades", {"currency_pair": symbol, "limit": min(limit, 1000)})

        def _trade(x):
            price = float(x["price"])
            qty = float(x["amount"])
            if price <= 0 or qty <= 0:
                raise ValueError("invalid trade record")
            side = str(x.get("side", "")).lower() or "unknown"
            return TradePrint(
                self.venue, "spot_usdt", symbol, self._time_ms(x.get("create_time_ms")),
                price, qty, quote_volume(price, qty), side,
                True if side in ("buy", "sell") else None, str(x.get("id")) if x.get("id") is not None else None, 0.78,
            )

        return parse_records(data, _trade)

    def _fetch_spot_orderbook(self, symbol, depth):
        data = self._get(f"{self.base}/spot/order_book", {"currency_pair": symbol, "limit": min(depth, 100)})
        bids = parse_book_levels(data.get("bids", []))
        asks = parse_book_levels(data.get("asks", []))
        require_non_empty_orderbook(venue=self.venue, market_type="spot_usdt", symbol=symbol, bids=bids, asks=asks)
        bb, ba = bids[0][0], asks[0][0]
        ts = self._time_ms(data.get("current")) if data.get("current") else now_ms()
        return OrderBookSnapshot(self.venue, "spot_usdt", symbol, ts, bids, asks, bb, ba, (bb + ba) / 2, ba - bb, min(len(bids), len(asks)), 0.78)

    # -- futures (USDT-settled) ----------------------------------------------

    def _fetch_perp_ohlcv(self, symbol, timeframe, limit):
        interval = self._require_timeframe(timeframe)
        mult = self._multiplier(symbol)
        data = self._get(
            f"{self.base}/futures/usdt/candlesticks",
            {"contract": symbol, "interval": interval, "limit": min(limit, 1999)},
        )

        def _bar(x):
            # dict: {t(s), o, h, l, c, v(contracts), sum(quote)}
            ts = self._time_ms(x["t"])
            op, hi, lo, cl = float(x["o"]), float(x["h"]), float(x["l"]), float(x["c"])
            base_vol = float(x.get("v", 0)) * mult
            quote_vol = float(x["sum"]) if x.get("sum") else quote_volume(cl, base_vol)
            if min(op, hi, lo, cl) <= 0 or base_vol < 0:
                raise ValueError("invalid bar record")
            return OHLCVBar(self.venue, "perp_usdt", symbol, timeframe, ts, op, hi, lo, cl, base_vol, quote_vol, None, 0.8)

        return parse_records(data, _bar)

    def _fetch_perp_trades(self, symbol, limit):
        mult = self._multiplier(symbol)
        data = self._get(f"{self.base}/futures/usdt/trades", {"contract": symbol, "limit": min(limit, 1000)})

        def _trade(x):
            price = float(x["price"])
            raw_size = float(x["size"])  # signed: negative = taker sell
            qty = abs(raw_size) * mult
            if price <= 0 or qty <= 0:
                raise ValueError("invalid trade record")
            side = "buy" if raw_size > 0 else "sell"
            return TradePrint(
                self.venue, "perp_usdt", symbol, self._time_ms(x.get("create_time_ms") or x.get("create_time")),
                price, qty, quote_volume(price, qty), side, True, str(x.get("id")) if x.get("id") is not None else None, 0.78,
            )

        return parse_records(data, _trade)

    def _fetch_perp_orderbook(self, symbol, depth):
        mult = self._multiplier(symbol)
        data = self._get(f"{self.base}/futures/usdt/order_book", {"contract": symbol, "limit": min(depth, 100)})
        bids = [(float(lvl["p"]), float(lvl["s"]) * mult) for lvl in data.get("bids", []) if float(lvl.get("s", 0)) > 0]
        asks = [(float(lvl["p"]), float(lvl["s"]) * mult) for lvl in data.get("asks", []) if float(lvl.get("s", 0)) > 0]
        require_non_empty_orderbook(venue=self.venue, market_type="perp_usdt", symbol=symbol, bids=bids, asks=asks)
        bb, ba = bids[0][0], asks[0][0]
        ts = self._time_ms(data.get("current")) if data.get("current") else now_ms()
        return OrderBookSnapshot(self.venue, "perp_usdt", symbol, ts, bids, asks, bb, ba, (bb + ba) / 2, ba - bb, min(len(bids), len(asks)), 0.78)

    # -- dispatch -------------------------------------------------------------

    def fetch_ohlcv(self, symbol, market_type, timeframe, limit):
        if market_type == "perp_usdt":
            return self._fetch_perp_ohlcv(symbol, timeframe, limit)
        return self._fetch_spot_ohlcv(symbol, timeframe, limit)

    def fetch_recent_trades(self, symbol, market_type, limit):
        if market_type == "perp_usdt":
            return self._fetch_perp_trades(symbol, limit)
        return self._fetch_spot_trades(symbol, limit)

    def fetch_orderbook(self, symbol, market_type, depth):
        if market_type == "perp_usdt":
            return self._fetch_perp_orderbook(symbol, depth)
        return self._fetch_spot_orderbook(symbol, depth)

    def fetch_funding(self, symbol, market_type):
        if market_type != "perp_usdt":
            return None
        data = self._get(f"{self.base}/futures/usdt/funding_rate", {"contract": symbol, "limit": 1})
        if not data:
            return None
        x = data[0]
        return FundingSnapshot(self.venue, market_type, symbol, self._time_ms(x.get("t")), float(x.get("r", 0)), None, 0.78)

    def fetch_open_interest(self, symbol, market_type):
        if market_type != "perp_usdt":
            return None
        data = self._get(f"{self.base}/futures/usdt/tickers", {"contract": symbol})
        ticker = data[0] if isinstance(data, list) and data else data
        if not isinstance(ticker, dict):
            return None
        total = ticker.get("total_size")
        if total is None:
            return None
        oi = float(total) * self._multiplier(symbol)
        return OpenInterestSnapshot(self.venue, market_type, symbol, now_ms(), oi, None, 0.78)
