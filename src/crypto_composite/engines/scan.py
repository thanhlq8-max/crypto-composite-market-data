from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from crypto_composite.symbol_map import resolve_symbol
from crypto_composite.connectors.binance import BinanceConnector
from crypto_composite.connectors.okx import OKXConnector
from crypto_composite.connectors.bybit import BybitConnector
from crypto_composite.connectors.coinbase import CoinbaseConnector
from crypto_composite.connectors.kraken import KrakenConnector
from crypto_composite.schemas import DataQualityReport
from crypto_composite.utils import now_ms

CONNECTORS = {"binance": BinanceConnector, "okx": OKXConnector, "bybit": BybitConnector, "coinbase": CoinbaseConnector, "kraken": KrakenConnector}


class ScanInputError(ValueError):
    pass


def _normalize_venues(venues: list[str]) -> list[str]:
    normalized = [v.strip().lower() for v in venues if v.strip()]
    unsupported = [v for v in normalized if v not in CONNECTORS]
    if unsupported:
        supported = ",".join(sorted(CONNECTORS))
        raise ScanInputError(f"VENUE_UNSUPPORTED venues={unsupported!r} supported={supported}")
    return normalized


def _scan_venue(venue: str, asset: str, market_types: list[str], timeframe: str, limit: int, depth: int) -> dict:
    """Fetch all market types for one venue sequentially (per-venue pacing)."""
    conn = CONNECTORS[venue]()
    data = {"ohlcv": [], "trades": [], "orderbooks": [], "funding": [], "open_interest": []}
    errors: list[dict] = []
    missing: list[str] = []
    venue_had_ok = False
    for mt in market_types:
        try:
            symbol = resolve_symbol(asset, venue, mt)
            bars = conn.fetch_ohlcv(symbol, mt, timeframe, limit)
            trades = conn.fetch_recent_trades(symbol, mt, min(limit, 300))
            book = conn.fetch_orderbook(symbol, mt, depth)
            data["ohlcv"].extend(bars)
            data["trades"].extend(trades)
            data["orderbooks"].append(book)
            if mt == "perp_usdt":
                f = conn.fetch_funding(symbol, mt)
                oi = conn.fetch_open_interest(symbol, mt)
                if f: data["funding"].append(f)
                else: missing.append(f"{venue}:{mt}:funding")
                if oi: data["open_interest"].append(oi)
                else: missing.append(f"{venue}:{mt}:open_interest")
            venue_had_ok = True
        except Exception as exc:
            errors.append({"venue": venue, "market_type": mt, "error": str(exc)})
    return {"venue": venue, "data": data, "errors": errors, "missing": missing, "ok": venue_had_ok}


def scan(asset: str, venues: list[str], market_types: list[str], timeframe: str, limit: int, depth: int = 100) -> dict:
    venues = _normalize_venues(venues)
    out = {"asset": asset, "generated_at_ms": now_ms(), "phase": "PHASE_1_DATA_FOUNDATION",
           "venues": venues, "timeframe": timeframe, "market_types": market_types,
           "data": {"ohlcv": [], "trades": [], "orderbooks": [], "funding": [], "open_interest": []},
           "errors": []}
    venues_ok, venues_failed = set(), set()
    missing = []
    # Venues are independent public endpoints: fetch them concurrently, one
    # worker per venue, sequential inside a venue. executor.map preserves the
    # input venue order so artifacts stay deterministic.
    if venues:
        with ThreadPoolExecutor(max_workers=len(venues)) as executor:
            results = list(executor.map(
                lambda v: _scan_venue(v, asset, market_types, timeframe, limit, depth), venues
            ))
    else:
        results = []
    for res in results:
        for key, records in res["data"].items():
            out["data"][key].extend(records)
        out["errors"].extend(res["errors"])
        missing.extend(res["missing"])
        if res["ok"]: venues_ok.add(res["venue"])
        else: venues_failed.add(res["venue"])
    qualities = []
    for records in out["data"].values():
        for r in records:
            qualities.append(getattr(r, "data_quality", 0.0))
    overall = sum(qualities)/len(qualities) if qualities else 0.0
    status = "OK" if len(venues_ok)>=2 and overall>=0.65 else ("PARTIAL" if len(venues_ok)>=1 and overall>=0.40 else "INSUFFICIENT_DATA")
    out["quality_report"] = DataQualityReport(asset, venues, sorted(venues_ok), sorted(venues_failed), market_types, timeframe, missing, overall, status)
    return out
