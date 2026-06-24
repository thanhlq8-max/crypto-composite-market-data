$ErrorActionPreference = 'Stop'

$repo = Get-Location
Write-Host "Applying v0.12.0 Kraken spot connector patch in $repo"

$py = @'
from pathlib import Path

ROOT = Path.cwd()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def replace(path: str, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        raise SystemExit(f"PATCH_ANCHOR_NOT_FOUND path={path!r} anchor={old[:120]!r}")
    write(path, text.replace(old, new))

# Version bump.
replace("pyproject.toml", 'version = "0.11.1"', 'version = "0.12.0"')
replace("src/crypto_composite/__init__.py", '__version__ = "0.11.1"', '__version__ = "0.12.0"')

# New Kraken connector. Public spot REST only.
write("src/crypto_composite/connectors/kraken.py", '''from __future__ import annotations

from typing import Any

from crypto_composite.connectors.base import (
    ConnectorDataError,
    ConnectorInputError,
    ExchangeConnector,
    parse_book_levels,
    require_non_empty_orderbook,
    require_timeframe,
)
from crypto_composite.schemas import FundingSnapshot, OHLCVBar, OpenInterestSnapshot, OrderBookSnapshot, TradePrint
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
        out = []
        for x in candles:
            ts = self._time_ms(x[0])
            op = float(x[1])
            hi = float(x[2])
            lo = float(x[3])
            cl = float(x[4])
            vol = float(x[6])
            trades = int(x[7]) if len(x) > 7 else None
            out.append(
                OHLCVBar(
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
            )
        return out[-min(limit, 720) :] if limit > 0 else out

    def fetch_recent_trades(self, symbol, market_type, limit):
        self._require_spot(market_type)
        data = self._get(f"{self.base}/Trades", {"pair": symbol, "count": min(limit, 1000)})
        trades = self._pair_payload(data)
        out = []
        for x in trades:
            price = float(x[0])
            qty = float(x[1])
            side_raw = str(x[3]).lower() if len(x) > 3 else ""
            side = "buy" if side_raw == "b" else "sell" if side_raw == "s" else "unknown"
            out.append(
                TradePrint(
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
            )
        return out

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
''')

# Symbol map: add Kraken as spot-only optional venue.
symbol_map = read("src/crypto_composite/symbol_map.py")
symbol_map = symbol_map.replace('SUPPORTED_VENUES = {"binance", "okx", "bybit", "coinbase"}', 'SUPPORTED_VENUES = {"binance", "okx", "bybit", "coinbase", "kraken"}')
symbol_map = symbol_map.replace(
    "Supported scope is explicit: Binance, OKX, Bybit, and optional Coinbase\n    Exchange spot. The mapper does not verify live exchange listings;",
    "Supported scope is explicit: Binance, OKX, Bybit, optional Coinbase\n    Exchange spot, and optional Kraken spot. The mapper does not verify live exchange listings;",
)
symbol_map = symbol_map.replace(
    "    if venue == \"coinbase\" and market_type == \"perp_usdt\":\n        raise SymbolMappingError(\"MARKET_TYPE_UNSUPPORTED venue='coinbase' market_type='perp_usdt'; Coinbase connector supports spot_usdt only\")\n    if venue == \"okx\" and market_type == \"spot_usdt\":",
    "    if venue == \"coinbase\" and market_type == \"perp_usdt\":\n        raise SymbolMappingError(\"MARKET_TYPE_UNSUPPORTED venue='coinbase' market_type='perp_usdt'; Coinbase connector supports spot_usdt only\")\n    if venue == \"kraken\" and market_type == \"spot_usdt\":\n        kraken_base = \"XBT\" if base == \"BTC\" else base\n        return f\"{kraken_base}{quote}\"\n    if venue == \"kraken\" and market_type == \"perp_usdt\":\n        raise SymbolMappingError(\"MARKET_TYPE_UNSUPPORTED venue='kraken' market_type='perp_usdt'; Kraken connector supports spot_usdt only\")\n    if venue == \"okx\" and market_type == \"spot_usdt\":",
)
write("src/crypto_composite/symbol_map.py", symbol_map)

# Register connector in scan engine.
scan = read("src/crypto_composite/engines/scan.py")
scan = scan.replace("from crypto_composite.connectors.coinbase import CoinbaseConnector\n", "from crypto_composite.connectors.coinbase import CoinbaseConnector\nfrom crypto_composite.connectors.kraken import KrakenConnector\n")
scan = scan.replace(
    'CONNECTORS = {"binance": BinanceConnector, "okx": OKXConnector, "bybit": BybitConnector, "coinbase": CoinbaseConnector}',
    'CONNECTORS = {"binance": BinanceConnector, "okx": OKXConnector, "bybit": BybitConnector, "coinbase": CoinbaseConnector, "kraken": KrakenConnector}',
)
write("src/crypto_composite/engines/scan.py", scan)

# Extend connector contract tests.
tests = read("tests/test_connector_contracts.py")
tests = tests.replace("from crypto_composite.connectors.coinbase import CoinbaseConnector\n", "from crypto_composite.connectors.coinbase import CoinbaseConnector\nfrom crypto_composite.connectors.kraken import KrakenConnector\n")
tests = tests.replace("        (CoinbaseConnector(), \"BTC-USDT\"),\n", "        (CoinbaseConnector(), \"BTC-USDT\"),\n        (KrakenConnector(), \"XBTUSDT\"),\n")
tests = tests.replace(
    "        (CoinbaseConnector(), \"BTC-USDT\", {\"bids\": [], \"asks\": [], \"time\": \"2023-11-14T22:13:20.000Z\"}),\n",
    "        (CoinbaseConnector(), \"BTC-USDT\", {\"bids\": [], \"asks\": [], \"time\": \"2023-11-14T22:13:20.000Z\"}),\n        (KrakenConnector(), \"XBTUSDT\", {\"error\": [], \"result\": {\"XBTUSDT\": {\"bids\": [], \"asks\": []}}}),\n",
)
insert_after = '''def test_coinbase_symbol_mapping_is_spot_only() -> None:\n    assert resolve_symbol("BTC-USDT", "coinbase", "spot_usdt") == "BTC-USDT"\n    with pytest.raises(SymbolMappingError, match="Coinbase connector supports spot_usdt only"):\n        resolve_symbol("BTC-USDT", "coinbase", "perp_usdt")\n\n\n'''
kraken_tests = '''def test_kraken_connector_parses_public_payloads(monkeypatch) -> None:\n    connector = KrakenConnector()\n\n    def fake_get(url: str, params: dict | None = None):\n        if "OHLC" in url:\n            return {\n                "error": [],\n                "result": {\n                    "XBTUSDT": [[1700000000, "100", "110", "90", "105", "104", "2", 12]],\n                    "last": 1700000000,\n                },\n            }\n        if "Trades" in url:\n            return {\n                "error": [],\n                "result": {\n                    "XBTUSDT": [["105", "0.5", 1700000001.25, "b", "m", "", 123]],\n                    "last": "1700000001250000000",\n                },\n            }\n        if "Depth" in url:\n            return {\n                "error": [],\n                "result": {\n                    "XBTUSDT": {\n                        "bids": [["104", "1.0", 1700000001]],\n                        "asks": [["106", "1.5", 1700000002]],\n                    }\n                },\n            }\n        raise AssertionError(url)\n\n    monkeypatch.setattr(connector, "_get", fake_get)\n\n    bars = connector.fetch_ohlcv("XBTUSDT", "spot_usdt", "15m", 1)\n    trades = connector.fetch_recent_trades("XBTUSDT", "spot_usdt", 1)\n    book = connector.fetch_orderbook("XBTUSDT", "spot_usdt", 10)\n\n    assert bars[0].timestamp_ms == 1700000000000\n    assert bars[0].volume_quote == 210.0\n    assert bars[0].trade_count == 12\n    assert trades[0].timestamp_ms == 1700000001250\n    assert trades[0].side == "buy"\n    assert trades[0].is_aggressive is True\n    assert book.best_bid == 104.0\n    assert book.best_ask == 106.0\n    assert book.mid == 105.0\n\n\ndef test_kraken_symbol_mapping_is_spot_only() -> None:\n    assert resolve_symbol("BTC-USDT", "kraken", "spot_usdt") == "XBTUSDT"\n    assert resolve_symbol("ETH-USDT", "kraken", "spot_usdt") == "ETHUSDT"\n    with pytest.raises(SymbolMappingError, match="Kraken connector supports spot_usdt only"):\n        resolve_symbol("BTC-USDT", "kraken", "perp_usdt")\n\n\n'''
if insert_after not in tests:
    raise SystemExit("PATCH_ANCHOR_NOT_FOUND tests coinbase symbol block")
tests = tests.replace(insert_after, insert_after + kraken_tests)
write("tests/test_connector_contracts.py", tests)

# README updates.
readme = read("README.md")
readme = readme.replace(
    "public Binance, OKX, Bybit and optional Coinbase Exchange spot endpoints",
    "public Binance, OKX, Bybit and optional Coinbase Exchange / Kraken spot endpoints",
)
readme = readme.replace(
    "Supports optional Coinbase Exchange public spot data without private account or order APIs.",
    "Supports optional Coinbase Exchange and Kraken public spot data without private account or order APIs.",
)
readme = readme.replace(
    "## Optional Coinbase spot connector\n\nCoinbase Exchange can be used as an additional public spot venue. Use `spot_usdt` only:\n",
    "## Optional spot-only connectors\n\nCoinbase Exchange and Kraken can be used as additional public spot venues. Use `spot_usdt` only:\n",
)
readme = readme.replace(
    "  --venues binance,okx,bybit,coinbase \\\n",
    "  --venues binance,okx,bybit,coinbase,kraken \\\n",
)
readme = readme.replace(
    "See [docs/COINBASE_CONNECTOR.md](docs/COINBASE_CONNECTOR.md).",
    "See [docs/COINBASE_CONNECTOR.md](docs/COINBASE_CONNECTOR.md) and [docs/KRAKEN_CONNECTOR.md](docs/KRAKEN_CONNECTOR.md).",
)
readme = readme.replace(
    "| Venues | Binance, OKX, Bybit; Coinbase Exchange spot-only |",
    "| Venues | Binance, OKX, Bybit; Coinbase Exchange and Kraken spot-only |",
)
write("README.md", readme)

# Roadmap updates.
roadmap = read("docs/ROADMAP.md")
roadmap += '''\n\n## v0.12 - Kraken spot connector\n\nGoal: expand optional public spot venue coverage while preserving the public-data-only boundary.\n\n- Optional `kraken` venue.\n- Public spot OHLCV, recent trades, and level-2 orderbook snapshots.\n- `spot_usdt` only; no Kraken perpetual/funding/open-interest support in this release.\n- Mocked parser tests and connector contract tests.\n- No ranking, signal, prediction, execution, or financial-advice semantics.\n'''
write("docs/ROADMAP.md", roadmap)

# Kraken connector docs.
write("docs/KRAKEN_CONNECTOR.md", '''# Kraken public spot connector\n\nVersion: v0.12.0\n\n`kraken` is an optional public spot venue for `crypto-composite-market-data`.\n\n## Supported scope\n\n- Market type: `spot_usdt` only.\n- Asset input: `BASE-USDT`, for example `BTC-USDT`.\n- BTC is mapped to Kraken's XBT pair naming for public REST requests.\n- Timeframes: `1m`, `5m`, `15m`, `1h`.\n- Public REST OHLCV, recent trades, and level-2 orderbook snapshots.\n\n## Unsupported scope\n\n- Kraken private account APIs.\n- Authenticated requests.\n- Order placement or account operations.\n- Kraken derivatives, funding, or open-interest data.\n- Ranking, prediction, trading signals, execution logic, position sizing, or financial advice.\n\n## Example\n\n```bash\ncrypto-composite run \\\n  --asset BTC-USDT \\\n  --venues binance,okx,bybit,coinbase,kraken \\\n  --market-types spot_usdt \\\n  --timeframes 15m \\\n  --out-dir artifacts-spot\n```\n\nKraken is intentionally optional. Default venue examples continue to use Binance, OKX, and Bybit unless the user explicitly requests additional spot venues.\n''')

# Release notes.
write("RELEASE_NOTES_v0.12.0.md", '''# Release Notes - v0.12.0\n\n## Summary\n\nv0.12.0 adds an optional Kraken public spot connector.\n\n## Added\n\n- `src/crypto_composite/connectors/kraken.py`.\n- Optional `kraken` venue registration.\n- Kraken `spot_usdt` symbol mapping.\n- Mocked parser tests for public OHLCV, recent trades, and orderbook payloads.\n- Spot-only symbol mapping test for Kraken.\n- Kraken connector documentation.\n\n## Scope boundary\n\n- Public REST data only.\n- `spot_usdt` only.\n- No private APIs.\n- No authenticated requests.\n- No order placement.\n- No ranking, prediction, trading-signal behavior, execution logic, position sizing, or financial advice.\n\n## Validation\n\nRun before commit/release:\n\n```bash\npython -m compileall src tests\npython -m pytest -q\npython -m build\n```\n''')

print("v0.12.0 Kraken spot connector patch applied")
'@

$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value $py -Encoding UTF8
py $tmp
Remove-Item $tmp -Force

Write-Host "v0.12.0 Kraken spot connector patch applied"
