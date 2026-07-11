from __future__ import annotations

from typing import Any

from crypto_composite.connectors.base import (
    ConnectorDataError,
    ConnectorInputError,
    ExchangeConnector,
    parse_book_levels,
    parse_records,
    require_non_empty_orderbook,
    require_timeframe,
)
from crypto_composite.schemas import OHLCVBar, OrderBookSnapshot, TradePrint
from crypto_composite.utils import now_ms, quote_volume

_INTERVAL = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}


class KrakenConnector(ExchangeConnector):
    venue = "kraken"
    base = "https://api.kraken.com/0/public"

    def _require_spot(self, market_type: str) -> None:
        if market_type != "spot_usdt":
            raise ConnectorInputError(
                f"MARKET_TYPE_UNSUPPORTED venue={self.venue} market_type={market_type!r} supported=spot_usdt"
            )

    def _public_result(self, data: dict[str, Any]) -> dict[str, Any]:
        errors = data.get("error") or []
        if errors:
            raise ConnectorDataError(f"KRAKEN_PUBLIC_ERROR venue={self.venue} errors={errors!r}")
        result = data.get("result")
        if not isinstance(result, dict):
            raise ConnectorDataError(f"KRAKEN_PUBLIC_RESULT_MISSING venue={self.venue}")
        return result

    def _pair_payload(self, data: dict[str, Any]) -> Any:
        result = self._public_result(data)
        for key, value in result.items():
            if key != "last":
                return value
        raise ConnectorDataError(f"KRAKEN_PAIR_PAYLOAD_MISSING venue={self.venue}")

    def _time_ms(self, value: Any) -> int:
        try:
            raw = float(value)
        except (TypeError, ValueError):
            return now_ms()
        return int(raw if raw >= 10_000_000_000 else raw * 1000)

    def fetch_ohlcv(self, symbol, market_type, timeframe, limit):
        self._require_spot(market_type)
        interval = require_timeframe(timeframe, _INTERVAL, venue=self.venue)
        data = self._get(f"{self.base}/OHLC", {"pair": symbol, "interval": interval})
        candles = self._pair_payload(data)

        def _bar(x):
            ts = self._time_ms(x[0])
            op = float(x[1])
            hi = float(x[2])
            lo = float(x[3])
            cl = float(x[4])
            vol = float(x[6])
            if min(op, hi, lo, cl) <= 0 or vol < 0:
                raise ValueError("invalid bar record")
            trades = int(x[7]) if len(x) > 7 else None
            return OHLCVBar(
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
                trades,
                0.82,
            )

        out = parse_records(candles, _bar)
        return out[-min(limit, 720) :] if limit > 0 else out

    def fetch_recent_trades(self, symbol, market_type, limit):
        self._require_spot(market_type)
        data = self._get(f"{self.base}/Trades", {"pair": symbol, "count": min(limit, 1000)})
        trades = self._pair_payload(data)

        def _trade(x):
            price = float(x[0])
            qty = float(x[1])
            if price <= 0 or qty <= 0:
                raise ValueError("invalid trade record")
            side_raw = str(x[3]).lower() if len(x) > 3 else ""
            side = "buy" if side_raw == "b" else "sell" if side_raw == "s" else "unknown"
            return TradePrint(
                self.venue,
                market_type,
                symbol,
                self._time_ms(x[2] if len(x) > 2 else None),
                price,
                qty,
                quote_volume(price, qty),
                side,
                True if side in ("buy", "sell") else None,
                str(x[6]) if len(x) > 6 else None,
                0.78,
            )

        return parse_records(trades, _trade)

    def fetch_orderbook(self, symbol, market_type, depth):
        self._require_spot(market_type)
        data = self._get(f"{self.base}/Depth", {"pair": symbol, "count": min(depth, 500)})
        book = self._pair_payload(data)
        bids = parse_book_levels(book.get("bids", []))[:depth]
        asks = parse_book_levels(book.get("asks", []))[:depth]
        require_non_empty_orderbook(venue=self.venue, market_type=market_type, symbol=symbol, bids=bids, asks=asks)
        bb, ba = bids[0][0], asks[0][0]
        timestamps = []
        for level in list(book.get("bids", []))[:1] + list(book.get("asks", []))[:1]:
            if len(level) > 2:
                timestamps.append(self._time_ms(level[2]))
        ts = max(timestamps) if timestamps else now_ms()
        return OrderBookSnapshot(
            self.venue,
            market_type,
            symbol,
            ts,
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
