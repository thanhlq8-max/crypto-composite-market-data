"""Live smoke test for public exchange connector schemas.

Runs every supported venue x market_type against the live public endpoints and
asserts the parsed records still match the documented artifact schema: field
presence, plausible timestamps, positive prices, bid/ask ordering, and a
quote/(base*close) unit-scale ratio that catches a contract-unit regression
(perp size left in contracts) before it reaches artifacts.

Usage (network required; NOT part of CI — live endpoints rate-limit and flake):

    python scripts/live_smoke.py [--asset BTC-USDT] [--timeframe 15m] [--limit 50]
    python scripts/live_smoke.py --evidence-out docs/live-verification

With --evidence-out, a dated live_verification_<UTC>.json/.md record of what the
run observed is written, so an E3-mocked -> E3+live promotion has a committable
artifact. Exit code 0 when every check passes, 1 otherwise. Output is a per-check
table so a single failing venue is visible without killing the other checks.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from crypto_composite.engines.scan import CONNECTORS
from crypto_composite.symbol_map import resolve_symbol, venue_supports_market_type

MARKET_TYPES = ["spot_usdt", "perp_usdt"]

# Plausibility window for record timestamps: not before 2020, not more than
# one day into the future (venue clock skew stays far below that).
MIN_TS_MS = 1_577_836_800_000
MAX_FUTURE_MS = 86_400_000


class CheckFailure(AssertionError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def _plausible_ts(ts: int, label: str, now_ms: int) -> None:
    _require(isinstance(ts, int), f"{label}: timestamp_ms not int: {ts!r}")
    _require(MIN_TS_MS < ts < now_ms + MAX_FUTURE_MS, f"{label}: timestamp_ms implausible: {ts}")


def check_ohlcv(conn, symbol: str, market_type: str, timeframe: str, limit: int) -> str:
    now = int(time.time() * 1000)
    bars = conn.fetch_ohlcv(symbol, market_type, timeframe, limit)
    _require(len(bars) > 0, "no bars returned")
    for b in bars[-5:]:
        _plausible_ts(b.timestamp_ms, "ohlcv", now)
        _require(b.open > 0 and b.high > 0 and b.low > 0 and b.close > 0, f"non-positive price in bar ts={b.timestamp_ms}")
        _require(b.high >= b.low, f"high < low in bar ts={b.timestamp_ms}")
        _require(b.high >= max(b.open, b.close) - 1e-9, f"high below open/close ts={b.timestamp_ms}")
        _require(b.low <= min(b.open, b.close) + 1e-9, f"low above open/close ts={b.timestamp_ms}")
        _require(b.volume_base >= 0, f"negative base volume ts={b.timestamp_ms}")
        _require(b.volume_quote is None or b.volume_quote >= 0, f"negative quote volume ts={b.timestamp_ms}")
    timestamps = [b.timestamp_ms for b in bars]
    _require(timestamps == sorted(timestamps), "bars not in ascending timestamp order")
    # Unit-scale sanity: quote volume ~= VWAP x base volume, so quote/(base*close)
    # sits near 1. A wrong contract-unit scale (perp base volume left in contracts,
    # the historical OKX/Gate class of bug) would push the ratio far off 1. The band
    # is generous so an honest VWAP != close never trips it.
    ratios = sorted(
        b.volume_quote / (b.volume_base * b.close)
        for b in bars
        if b.volume_quote is not None and b.volume_base > 0 and b.close > 0
    )
    detail = f"{len(bars)} bars, last close={bars[-1].close}"
    if ratios:
        median_ratio = ratios[len(ratios) // 2]
        _require(
            0.5 <= median_ratio <= 2.0,
            f"quote/(base*close) median implausible: {median_ratio:.4f} (unit-scale regression?)",
        )
        detail += f", qv/(base*close)~{median_ratio:.3f}"
    return detail


def check_trades(conn, symbol: str, market_type: str, limit: int) -> str:
    now = int(time.time() * 1000)
    trades = conn.fetch_recent_trades(symbol, market_type, limit)
    _require(len(trades) > 0, "no trades returned")
    for t in trades[:20]:
        _plausible_ts(t.timestamp_ms, "trade", now)
        _require(t.price > 0, f"non-positive trade price {t.price}")
        _require(t.size_base > 0, f"non-positive trade size {t.size_base}")
        _require(t.side in ("buy", "sell", "unknown"), f"unexpected side token {t.side!r}")
    return f"{len(trades)} trades, last price={trades[-1].price}"


def check_orderbook(conn, symbol: str, market_type: str, depth: int) -> str:
    now = int(time.time() * 1000)
    book = conn.fetch_orderbook(symbol, market_type, depth)
    _plausible_ts(book.timestamp_ms, "orderbook", now)
    _require(len(book.bids) > 0 and len(book.asks) > 0, "empty book side")
    _require(book.best_bid > 0 and book.best_ask > 0, "non-positive best bid/ask")
    _require(book.best_bid < book.best_ask, f"crossed book: bid={book.best_bid} ask={book.best_ask}")
    _require(book.spread >= 0, f"negative spread {book.spread}")
    bid_prices = [p for p, _ in book.bids[:10]]
    ask_prices = [p for p, _ in book.asks[:10]]
    _require(bid_prices == sorted(bid_prices, reverse=True), "bids not descending")
    _require(ask_prices == sorted(ask_prices), "asks not ascending")
    return f"bid={book.best_bid} ask={book.best_ask} levels={min(len(book.bids), len(book.asks))}"


def check_funding(conn, symbol: str, market_type: str) -> str:
    snap = conn.fetch_funding(symbol, market_type)
    _require(snap is not None, "no funding snapshot for perp venue")
    _require(abs(snap.funding_rate) < 0.05, f"funding rate implausible: {snap.funding_rate}")
    return f"rate={snap.funding_rate}"


def check_open_interest(conn, symbol: str, market_type: str) -> str:
    snap = conn.fetch_open_interest(symbol, market_type)
    _require(snap is not None, "no open-interest snapshot for perp venue")
    _require(snap.open_interest_base > 0, f"non-positive open interest: {snap.open_interest_base}")
    return f"oi={snap.open_interest_base}"


def _write_evidence(out_dir: str, asset: str, timeframe: str,
                    results: list[tuple[str, str, str]], passed: int) -> Path:
    """Persist a dated, committable record of what the live run observed.

    This is the E3-mocked -> E3+live promotion evidence: it captures which venue
    endpoints answered and the observed per-check detail (record counts, sample
    prices, the quote/(base*close) unit ratio) at a fixed UTC timestamp.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": stamp,
        "asset": asset,
        "timeframe": timeframe,
        "summary": {"passed": passed, "total": len(results)},
        "checks": [{"check": cid, "status": status, "detail": detail}
                   for cid, status, detail in results],
        "boundary": "Public market data only; live-verification evidence, no trading semantics.",
    }
    (out / f"live_verification_{stamp}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    lines = [
        f"# Live connector verification — {stamp}",
        "",
        f"Asset `{asset}` · timeframe `{timeframe}` · {passed}/{len(results)} checks passed.",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    lines += [f"| `{cid}` | {status} | {detail} |" for cid, status, detail in results]
    md_path = out / f"live_verification_{stamp}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path


def run(asset: str, timeframe: str, limit: int, depth: int, evidence_out: str | None = None) -> int:
    results: list[tuple[str, str, str]] = []  # (check id, PASS/FAIL, detail)
    failures = 0
    for venue, connector_cls in sorted(CONNECTORS.items()):
        conn = connector_cls()
        for market_type in MARKET_TYPES:
            if not venue_supports_market_type(venue, market_type):
                continue
            symbol = resolve_symbol(asset, venue, market_type)
            checks = [
                ("ohlcv", lambda: check_ohlcv(conn, symbol, market_type, timeframe, limit)),
                ("trades", lambda: check_trades(conn, symbol, market_type, min(limit, 100))),
                ("orderbook", lambda: check_orderbook(conn, symbol, market_type, depth)),
            ]
            if market_type == "perp_usdt":
                checks.append(("funding", lambda: check_funding(conn, symbol, market_type)))
                checks.append(("open_interest", lambda: check_open_interest(conn, symbol, market_type)))
            for name, fn in checks:
                check_id = f"{venue}:{market_type}:{name}"
                try:
                    detail = fn()
                    results.append((check_id, "PASS", detail))
                except Exception as exc:  # live endpoint: report and keep going
                    failures += 1
                    results.append((check_id, "FAIL", str(exc)))
                time.sleep(0.2)  # stay far under public rate limits

    width = max(len(r[0]) for r in results)
    for check_id, status, detail in results:
        print(f"{check_id:<{width}}  {status}  {detail}")
    passed = len(results) - failures
    print(f"\n{passed}/{len(results)} checks passed")
    if evidence_out:
        evidence_path = _write_evidence(evidence_out, asset, timeframe, results, passed)
        print(f"evidence written: {evidence_path}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--asset", default="BTC-USDT")
    parser.add_argument("--timeframe", default="15m")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--depth", type=int, default=50)
    parser.add_argument(
        "--evidence-out",
        default=None,
        help="directory to write a dated live_verification_<UTC>.json/.md evidence record",
    )
    args = parser.parse_args()
    return run(args.asset, args.timeframe, args.limit, args.depth, args.evidence_out)


if __name__ == "__main__":
    sys.exit(main())
