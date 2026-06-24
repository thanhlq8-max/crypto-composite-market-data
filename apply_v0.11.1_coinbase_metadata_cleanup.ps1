$ErrorActionPreference = "Stop"

function Write-Utf8NoBomFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Resolve-Path -LiteralPath $Path), $Content, $utf8NoBom)
}

function Replace-InFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Old,
        [Parameter(Mandatory = $true)][string]$New
    )
    $text = Get-Content -LiteralPath $Path -Raw
    if (-not $text.Contains($Old)) {
        throw "Expected text not found in $Path"
    }
    $text = $text.Replace($Old, $New)
    Write-Utf8NoBomFile -Path $Path -Content $text
}

# Version bump: v0.11.0 -> v0.11.1
Replace-InFile -Path "pyproject.toml" -Old 'version = "0.11.0"' -New 'version = "0.11.1"'
Replace-InFile -Path "src\crypto_composite\__init__.py" -Old '__version__ = "0.11.0"' -New '__version__ = "0.11.1"'
Replace-InFile -Path "docs\ARTIFACT_SCHEMA.md" -Old 'package version `0.11.0`' -New 'package version `0.11.1`'

# Clean stale symbol-map wording without changing mapping behavior.
$symbolMap = @'
from __future__ import annotations


class SymbolMappingError(ValueError):
    pass


SUPPORTED_MARKET_TYPES = {"spot_usdt", "perp_usdt"}
SUPPORTED_VENUES = {"binance", "okx", "bybit", "coinbase"}


def _split_asset(asset: str) -> tuple[str, str]:
    parts = asset.upper().split("-")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise SymbolMappingError(
            f"ASSET_FORMAT_UNSUPPORTED asset={asset!r}; expected BASE-QUOTE, for example BTC-USDT"
        )
    return parts[0], parts[1]


def resolve_symbol(asset: str, venue: str, market_type: str) -> str:
    """Resolve BASE-QUOTE assets to public exchange symbols.

    Supported scope is explicit: Binance, OKX, Bybit, and optional Coinbase
    Exchange spot. The mapper does not verify live exchange listings;
    connector calls surface listing errors from the public API.
    """
    venue = venue.lower()
    market_type = market_type.lower()
    if venue not in SUPPORTED_VENUES:
        raise SymbolMappingError(f"VENUE_UNSUPPORTED venue={venue!r}")
    if market_type not in SUPPORTED_MARKET_TYPES:
        raise SymbolMappingError(f"MARKET_TYPE_UNSUPPORTED market_type={market_type!r}")
    base, quote = _split_asset(asset)
    if quote != "USDT":
        raise SymbolMappingError(f"QUOTE_UNSUPPORTED quote={quote!r}; only USDT pairs are supported")
    if venue in {"binance", "bybit"}:
        return f"{base}{quote}"
    if venue == "coinbase" and market_type == "spot_usdt":
        return f"{base}-{quote}"
    if venue == "coinbase" and market_type == "perp_usdt":
        raise SymbolMappingError("MARKET_TYPE_UNSUPPORTED venue='coinbase' market_type='perp_usdt'; Coinbase connector supports spot_usdt only")
    if venue == "okx" and market_type == "spot_usdt":
        return f"{base}-{quote}"
    if venue == "okx" and market_type == "perp_usdt":
        return f"{base}-{quote}-SWAP"
    raise SymbolMappingError(f"SYMBOL_MAPPING_MISSING asset={asset} venue={venue} market_type={market_type}")
'@
Write-Utf8NoBomFile -Path "src\crypto_composite\symbol_map.py" -Content $symbolMap

# Rewrite files created by the v0.11.0 PowerShell patch as UTF-8 without BOM.
$coinbase = @'
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
Write-Utf8NoBomFile -Path "src\crypto_composite\connectors\coinbase.py" -Content $coinbase

$coinbaseDoc = @'
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
Write-Utf8NoBomFile -Path "docs\COINBASE_CONNECTOR.md" -Content $coinbaseDoc

$releaseNotes = @'
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
Write-Utf8NoBomFile -Path "RELEASE_NOTES_v0.11.0.md" -Content $releaseNotes

$releaseNotes111 = @'
# v0.11.1 - Coinbase Metadata Cleanup

## Fixed

- Normalized Coinbase connector and docs files to UTF-8 without BOM.
- Updated `symbol_map.py` documentation wording to include Coinbase Exchange spot support.
- Removed stale `v0.1` wording from unsupported-quote error text.
- Updated artifact schema documentation package-version reference to `0.11.1`.

## Behavior

No connector behavior, artifact schema fields, CLI behavior, market-data semantics, or project boundaries changed.

## Validation

Expected local checks:

```bash
py -m compileall src tests
py -m pytest -q
py -m build
```
'@
Write-Utf8NoBomFile -Path "RELEASE_NOTES_v0.11.1.md" -Content $releaseNotes111

Add-Content -LiteralPath "docs\ROADMAP.md" -Value @'

## v0.11.1 - Coinbase metadata cleanup

Goal: clean source/documentation metadata after the Coinbase connector release without changing runtime behavior.

- Normalize new Coinbase files to UTF-8 without BOM.
- Update symbol-map wording to mention Coinbase Exchange spot support.
- Keep connector behavior and project boundary unchanged.
'@

Write-Host "v0.11.1 Coinbase metadata cleanup patch applied"
