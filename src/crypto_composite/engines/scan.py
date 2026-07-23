from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from crypto_composite.symbol_map import resolve_symbol, venue_supports_market_type
from crypto_composite.connectors.base import ExchangeConnector
from crypto_composite.connectors.binance import BinanceConnector
from crypto_composite.connectors.okx import OKXConnector
from crypto_composite.connectors.bybit import BybitConnector
from crypto_composite.connectors.coinbase import CoinbaseConnector
from crypto_composite.connectors.kraken import KrakenConnector
from crypto_composite.connectors.gate import GateConnector
from crypto_composite.schemas import DataQualityReport
from crypto_composite.utils import now_ms

CONNECTORS: dict[str, Callable[[], ExchangeConnector]] = {"binance": BinanceConnector, "okx": OKXConnector, "bybit": BybitConnector, "coinbase": CoinbaseConnector, "kraken": KrakenConnector, "gate": GateConnector}


class ScanInputError(ValueError):
    pass


def normalize_venues(venues: list[str]) -> list[str]:
    """Lowercase, validate, and de-duplicate venues preserving first-seen order.

    A duplicated venue used to be fetched twice: composite volume/depth
    totals doubled while set-based venue counts halved coverage — silently.
    """
    normalized = [v.strip().lower() for v in venues if v.strip()]
    unsupported = [v for v in normalized if v not in CONNECTORS]
    if unsupported:
        supported = ",".join(sorted(CONNECTORS))
        raise ScanInputError(f"VENUE_UNSUPPORTED venues={unsupported!r} supported={supported}")
    return list(dict.fromkeys(normalized))


def _fetch_optional(fetch, symbol: str, mt: str):
    """Funding/OI are enrichment: a failure degrades to missing, never to a
    market_type error — the already-fetched bars/trades/book stay valid."""
    try:
        return fetch(symbol, mt)
    except Exception:
        return None


def _scan_venue(venue: str, asset: str, market_types: list[str], timeframe: str, limit: int, depth: int) -> dict:
    """Fetch all market types for one venue sequentially (per-venue pacing)."""
    conn = CONNECTORS[venue]()
    data: dict[str, list[Any]] = {"ohlcv": [], "trades": [], "orderbooks": [], "funding": [], "open_interest": []}
    errors: list[dict] = []
    missing: list[str] = []
    venue_had_ok = False
    supported_any = False
    for mt in market_types:
        # Structural incapability (spot-only venue asked for perp) is not a
        # failure: record it as missing and keep the venue out of venues_failed.
        if not venue_supports_market_type(venue, mt):
            missing.append(f"{venue}:{mt}:unsupported_market_type")
            continue
        supported_any = True
        try:
            symbol = resolve_symbol(asset, venue, mt)
            bars = conn.fetch_ohlcv(symbol, mt, timeframe, limit)
            trades = conn.fetch_recent_trades(symbol, mt, min(limit, 300))
            book = conn.fetch_orderbook(symbol, mt, depth)
            data["ohlcv"].extend(bars)
            data["trades"].extend(trades)
            data["orderbooks"].append(book)
            # An endpoint that answers with zero parseable records must be
            # visible in the quality artifact, not silently "ok".
            if not bars:
                missing.append(f"{venue}:{mt}:ohlcv_empty")
            if not trades:
                missing.append(f"{venue}:{mt}:trades_empty")
            venue_had_ok = True
            if mt == "perp_usdt":
                f = _fetch_optional(conn.fetch_funding, symbol, mt)
                oi = _fetch_optional(conn.fetch_open_interest, symbol, mt)
                if f:
                    data["funding"].append(f)
                else:
                    missing.append(f"{venue}:{mt}:funding")
                if oi:
                    data["open_interest"].append(oi)
                else:
                    missing.append(f"{venue}:{mt}:open_interest")
        except Exception as exc:
            errors.append({"venue": venue, "market_type": mt, "error": str(exc)})
    return {
        "venue": venue,
        "data": data,
        "errors": errors,
        "missing": missing,
        "ok": venue_had_ok,
        "supported": supported_any,
    }


def scan(asset: str, venues: list[str], market_types: list[str], timeframe: str, limit: int, depth: int = 100) -> dict:
    venues = normalize_venues(venues)
    out: dict[str, Any] = {"asset": asset, "generated_at_ms": now_ms(), "phase": "PHASE_1_DATA_FOUNDATION",
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
        if res["ok"]:
            venues_ok.add(res["venue"])
        elif res["supported"]:
            venues_failed.add(res["venue"])
        # A venue with no supported market_type in this run belongs in
        # neither list; its missing entries already record why.
    qualities = []
    for records in out["data"].values():
        for r in records:
            qualities.append(getattr(r, "data_quality", 0.0))
    overall = sum(qualities)/len(qualities) if qualities else 0.0
    status = "OK" if len(venues_ok)>=2 and overall>=0.65 else ("PARTIAL" if len(venues_ok)>=1 and overall>=0.40 else "INSUFFICIENT_DATA")
    out["quality_report"] = DataQualityReport(asset, venues, sorted(venues_ok), sorted(venues_failed), market_types, timeframe, missing, overall, status)
    return out
