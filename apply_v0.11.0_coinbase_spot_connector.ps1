$ErrorActionPreference = "Stop"

if (-not (Test-Path "pyproject.toml")) {
    throw "Run this script from the crypto-composite-market-data repository root."
}
if (-not (Test-Path "src\crypto_composite\connectors")) {
    throw "Expected src\crypto_composite\connectors directory is missing."
}

New-Item -ItemType Directory -Force -Path "src\crypto_composite\connectors" | Out-Null
New-Item -ItemType Directory -Force -Path "docs" | Out-Null

Set-Content -Path "src\crypto_composite\connectors\coinbase.py" -Encoding UTF8 -Value @'
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from crypto_composite.connectors.base import (
    ConnectorInputError,
    ExchangeConnector,
    parse_book_levels,
    require_non_empty_orderbook,
    require_timeframe,
)
from crypto_composite.schemas import FundingSnapshot, OHLCVBar, OpenInterestSnapshot, OrderBookSnapshot, TradePrint
from crypto_composite.utils import now_ms, quote_volume

_INTERVAL = {"1m": "60", "5m": "300", "15m": "900", "1h": "3600"}


class CoinbaseConnector(ExchangeConnector):
    venue = "coinbase"
    base = "https://api.exchange.coinbase.com"

    def _require_spot(self, market_type: str) -> None:
        if market_type != "spot_usdt":
            raise ConnectorInputError(
                f"MARKET_TYPE_UNSUPPORTED venue={self.venue} market_type={market_type!r} supported=spot_usdt"
            )

    def _time_ms(self, value: Any) -> int:
        if isinstance(value, (int, float)):
            raw = float(value)
            return int(raw if raw >= 10_000_000_000 else raw * 1000)
        if isinstance(value, str):
            text = value.strip()
            try:
                if text.endswith("Z"):
                    dt = datetime.fromisoformat(text[:-1] + "+00:00")
                else:
                    dt = datetime.fromisoformat(text)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp() * 1000)
            except ValueError:
                return now_ms()
        return now_ms()

    def fetch_ohlcv(self, symbol, market_type, timeframe, limit):
        self._require_spot(market_type)
        granularity = require_timeframe(timeframe, _INTERVAL, venue=self.venue)
        data = self._get(f"{self.base}/products/{symbol}/candles", {"granularity": granularity})
        out = []
        for x in sorted(data, key=lambda item: int(item[0])):
            ts = self._time_ms(x[0])
            lo = float(x[1])
            hi = float(x[2])
            op = float(x[3])
            cl = float(x[4])
            vol = float(x[5])
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
                    None,
                    0.82,
                )
            )
        return out[-min(limit, 300) :] if limit > 0 else out

    def fetch_recent_trades(self, symbol, market_type, limit):
        self._require_spot(market_type)
        data = self._get(f"{self.base}/products/{symbol}/trades", {"limit": min(limit, 1000)})
        out = []
        for x in data:
            price = float(x["price"])
            qty = float(x["size"])
            maker_side = str(x.get("side", "")).lower()
            side = "sell" if maker_side == "buy" else "buy" if maker_side == "sell" else "unknown"
            out.append(
                TradePrint(
                    self.venue,
                    market_type,
                    symbol,
                    self._time_ms(x.get("time")),
                    price,
                    qty,
                    quote_volume(price, qty),
                    side,
                    True if side in ("buy", "sell") else None,
                    str(x.get("trade_id")) if x.get("trade_id") is not None else None,
                    0.78,
                )
            )
        return out

    def fetch_orderbook(self, symbol, market_type, depth):
        self._require_spot(market_type)
        data = self._get(f"{self.base}/products/{symbol}/book", {"level": 2})
        bids = parse_book_levels(data.get("bids", []))[:depth]
        asks = parse_book_levels(data.get("asks", []))[:depth]
        require_non_empty_orderbook(venue=self.venue, market_type=market_type, symbol=symbol, bids=bids, asks=asks)
        bb, ba = bids[0][0], asks[0][0]
        return OrderBookSnapshot(
            self.venue,
            market_type,
            symbol,
            self._time_ms(data.get("time")),
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

'@

Set-Content -Path "docs\COINBASE_CONNECTOR.md" -Encoding UTF8 -Value @'
# Coinbase Exchange spot connector

`crypto-composite-market-data` supports Coinbase Exchange as an optional public spot data source.

## Supported scope

| Area | Status |
|---|---|
| Public spot OHLCV candles | Supported |
| Public recent trades | Supported |
| Public level-2 orderbook snapshots | Supported |
| Perpetual / derivatives market type | Not supported |
| Funding / open interest | Not supported |
| Private account APIs | Not supported |
| Orders / execution | Not supported |

## Example

Use Coinbase with spot-only market types:

```bash
crypto-composite run \
  --asset BTC-USDT \
  --venues binance,okx,bybit,coinbase \
  --market-types spot_usdt \
  --timeframes 15m \
  --out-dir artifacts-spot
```

Coinbase product IDs are resolved from `BASE-USDT` to `BASE-USDT`, for example `BTC-USDT`. The connector does not pre-verify exchange listing availability; unsupported products surface as public API fetch errors.

## Boundary

This connector is market-data infrastructure only. It does not create rankings, predictions, trading signals, execution instructions, position sizing, profitability claims, or financial advice.

'@

Set-Content -Path "RELEASE_NOTES_v0.11.0.md" -Encoding UTF8 -Value @'
# v0.11.0 - Coinbase Exchange Spot Connector

## Added

- Added optional `coinbase` venue support for Coinbase Exchange public spot market-data endpoints.
- Added `src/crypto_composite/connectors/coinbase.py` for public spot OHLCV, recent trades, and level-2 orderbook snapshots.
- Added mocked parser and connector-contract tests for Coinbase.
- Added `docs/COINBASE_CONNECTOR.md`.

## Scope

Coinbase support is spot-only in this release. The connector does not add private account APIs, authenticated requests, order placement, derivatives, rankings, predictions, trading signals, execution instructions, position sizing, profitability claims, or financial advice.

## Validation

Expected local checks:

```bash
py -m compileall src tests
py -m pytest -q
py -m build
```

'@

$patch = @'
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"PATCH_CONTEXT_MISSING path={path} old={old!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Version bump
replace_once("pyproject.toml", 'version = "0.10.0"', 'version = "0.11.0"')
replace_once("src/crypto_composite/__init__.py", '__version__ = "0.10.0"', '__version__ = "0.11.0"')

# Connector registration
replace_once(
    "src/crypto_composite/engines/scan.py",
    "from crypto_composite.connectors.bybit import BybitConnector\n",
    "from crypto_composite.connectors.bybit import BybitConnector\nfrom crypto_composite.connectors.coinbase import CoinbaseConnector\n",
)
replace_once(
    "src/crypto_composite/engines/scan.py",
    'CONNECTORS = {"binance": BinanceConnector, "okx": OKXConnector, "bybit": BybitConnector}',
    'CONNECTORS = {"binance": BinanceConnector, "okx": OKXConnector, "bybit": BybitConnector, "coinbase": CoinbaseConnector}',
)

# Symbol mapping: Coinbase Exchange spot only.
replace_once(
    "src/crypto_composite/symbol_map.py",
    'SUPPORTED_VENUES = {"binance", "okx", "bybit"}',
    'SUPPORTED_VENUES = {"binance", "okx", "bybit", "coinbase"}',
)
replace_once(
    "src/crypto_composite/symbol_map.py",
    '    if venue in {"binance", "bybit"}:\n        return f"{base}{quote}"\n',
    '    if venue in {"binance", "bybit"}:\n        return f"{base}{quote}"\n    if venue == "coinbase" and market_type == "spot_usdt":\n        return f"{base}-{quote}"\n    if venue == "coinbase" and market_type == "perp_usdt":\n        raise SymbolMappingError("MARKET_TYPE_UNSUPPORTED venue=\\\'coinbase\\\' market_type=\\\'perp_usdt\\\'; Coinbase connector supports spot_usdt only")\n',
)

# Tests
replace_once(
    "tests/test_connector_contracts.py",
    "from crypto_composite.connectors.bybit import BybitConnector\n",
    "from crypto_composite.connectors.bybit import BybitConnector\nfrom crypto_composite.connectors.coinbase import CoinbaseConnector\n",
)
replace_once(
    "tests/test_connector_contracts.py",
    "from crypto_composite.engines.scan import ScanInputError, scan\n",
    "from crypto_composite.engines.scan import ScanInputError, scan\nfrom crypto_composite.symbol_map import SymbolMappingError, resolve_symbol\n",
)
replace_once(
    "tests/test_connector_contracts.py",
    '        (BybitConnector(), "BTCUSDT"),\n',
    '        (BybitConnector(), "BTCUSDT"),\n        (CoinbaseConnector(), "BTC-USDT"),\n',
)
replace_once(
    "tests/test_connector_contracts.py",
    '        (BybitConnector(), "BTCUSDT", {"result": {"b": [], "a": [], "ts": 1000}}),\n',
    '        (BybitConnector(), "BTCUSDT", {"result": {"b": [], "a": [], "ts": 1000}}),\n        (CoinbaseConnector(), "BTC-USDT", {"bids": [], "asks": [], "time": "2023-11-14T22:13:20.000Z"}),\n',
)
insert_after = '''def test_bybit_connector_parses_public_payloads(monkeypatch) -> None:\n    connector = BybitConnector()\n\n    def fake_get(url: str, params: dict | None = None):\n        if "kline" in url:\n            return {"result": {"list": [["1000", "100", "110", "90", "105", "2", "210"]]}}\n        if "recent-trade" in url:\n            return {"result": {"list": [{"time": "1010", "price": "105", "size": "0.5", "side": "Sell", "execId": "abc"}]}}\n        if "orderbook" in url:\n            return {"result": {"ts": 1020, "b": [["104", "1.0"]], "a": [["106", "1.5"]]}}\n        raise AssertionError(url)\n\n    monkeypatch.setattr(connector, "_get", fake_get)\n\n    bars = connector.fetch_ohlcv("BTCUSDT", "spot_usdt", "15m", 1)\n    trades = connector.fetch_recent_trades("BTCUSDT", "spot_usdt", 1)\n    book = connector.fetch_orderbook("BTCUSDT", "spot_usdt", 10)\n\n    assert bars[0].open == 100.0\n    assert bars[0].volume_quote == 210.0\n    assert trades[0].side == "sell"\n    assert trades[0].is_aggressive is True\n    assert book.mid == 105.0\n\n\n'''
coinbase_tests = '''def test_coinbase_connector_parses_public_payloads(monkeypatch) -> None:\n    connector = CoinbaseConnector()\n\n    def fake_get(url: str, params: dict | None = None):\n        if "candles" in url:\n            return [[1700000000, "90", "110", "100", "105", "2"]]\n        if "trades" in url:\n            return [\n                {\n                    "time": "2023-11-14T22:13:20.000Z",\n                    "trade_id": 123,\n                    "price": "105",\n                    "size": "0.5",\n                    "side": "sell",\n                }\n            ]\n        if "book" in url:\n            return {\n                "bids": [["104", "1.0", 2]],\n                "asks": [["106", "1.5", 1]],\n                "time": "2023-11-14T22:13:21.000Z",\n            }\n        raise AssertionError(url)\n\n    monkeypatch.setattr(connector, "_get", fake_get)\n\n    bars = connector.fetch_ohlcv("BTC-USDT", "spot_usdt", "15m", 1)\n    trades = connector.fetch_recent_trades("BTC-USDT", "spot_usdt", 1)\n    book = connector.fetch_orderbook("BTC-USDT", "spot_usdt", 10)\n\n    assert bars[0].timestamp_ms == 1700000000000\n    assert bars[0].volume_quote == 210.0\n    assert trades[0].side == "buy"\n    assert trades[0].is_aggressive is True\n    assert book.best_bid == 104.0\n    assert book.best_ask == 106.0\n    assert book.mid == 105.0\n\n\ndef test_coinbase_symbol_mapping_is_spot_only() -> None:\n    assert resolve_symbol("BTC-USDT", "coinbase", "spot_usdt") == "BTC-USDT"\n    with pytest.raises(SymbolMappingError, match="Coinbase connector supports spot_usdt only"):\n        resolve_symbol("BTC-USDT", "coinbase", "perp_usdt")\n\n\n'''
replace_once("tests/test_connector_contracts.py", insert_after, insert_after + coinbase_tests)
replace_once(
    "tests/test_connector_contracts.py",
    '        scan("BTC-USDT", ["binance", "coinbase"], ["spot_usdt"], "15m", 10, depth=5)\n',
    '        scan("BTC-USDT", ["binance", "unknownvenue"], ["spot_usdt"], "15m", 10, depth=5)\n',
)

# README updates
replace_once(
    "README.md",
    "`crypto-composite-market-data` builds reproducible JSON artifacts from public Binance, OKX and Bybit endpoints.",
    "`crypto-composite-market-data` builds reproducible JSON artifacts from public Binance, OKX, Bybit and optional Coinbase Exchange spot endpoints.",
)
replace_once(
    "README.md",
    "- Fetches public OHLCV, recent trades, orderbook snapshots, funding and open-interest data.\n",
    "- Fetches public OHLCV, recent trades, orderbook snapshots, funding and open-interest data.\n- Supports optional Coinbase Exchange public spot data without private account or order APIs.\n",
)
optional_coinbase_section = '''\n## Optional Coinbase spot connector\n\nCoinbase Exchange can be used as an additional public spot venue. Use `spot_usdt` only:\n\n```bash\ncrypto-composite run \\\n  --asset BTC-USDT \\\n  --venues binance,okx,bybit,coinbase \\\n  --market-types spot_usdt \\\n  --timeframes 15m \\\n  --out-dir artifacts-spot\n```\n\nSee [docs/COINBASE_CONNECTOR.md](docs/COINBASE_CONNECTOR.md).\n'''
replace_once(
    "README.md",
    "```\n\n## Useful output preview\n",
    "```\n" + optional_coinbase_section + "\n## Useful output preview\n",
)
replace_once(
    "README.md",
    "| Venues | Binance, OKX, Bybit |",
    "| Venues | Binance, OKX, Bybit; Coinbase Exchange spot-only |",
)
replace_once(
    "README.md",
    "- [docs/CSV_EXPORT.md](docs/CSV_EXPORT.md)\n",
    "- [docs/CSV_EXPORT.md](docs/CSV_EXPORT.md)\n- [docs/COINBASE_CONNECTOR.md](docs/COINBASE_CONNECTOR.md)\n",
)

# Docs
replace_once("docs/ARTIFACT_SCHEMA.md", "package version `0.9.0`", "package version `0.11.0`")
replace_once(
    "docs/ROADMAP.md",
    "## v0.10 ??? CSV artifact interoperability\n",
    "## v0.10 - CSV artifact interoperability\n",
)
roadmap_tail = '''\n\n## v0.11 - Coinbase Exchange spot connector\n\nGoal: expand public venue coverage without adding private account APIs, derivatives assumptions, or execution semantics.\n\n- Optional `coinbase` venue.\n- Public spot OHLCV, recent trades, and level-2 orderbook snapshots.\n- `spot_usdt` only; no Coinbase perpetual/funding/open-interest support in this release.\n- Mocked parser tests and connector contract tests.\n- No ranking, signal, prediction, execution, or financial-advice semantics.\n'''
roadmap = Path("docs/ROADMAP.md")
text = roadmap.read_text(encoding="utf-8")
if "## v0.11 - Coinbase Exchange spot connector" not in text:
    roadmap.write_text(text.rstrip() + roadmap_tail, encoding="utf-8")

print("v0.11.0 Coinbase spot connector patch applied")
'@

$patch | py -
