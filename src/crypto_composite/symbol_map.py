from __future__ import annotations


class SymbolMappingError(ValueError):
    pass


SUPPORTED_MARKET_TYPES = {"spot_usdt", "perp_usdt"}
SUPPORTED_VENUES = {"binance", "okx", "bybit", "coinbase", "kraken"}


def _split_asset(asset: str) -> tuple[str, str]:
    parts = asset.upper().split("-")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise SymbolMappingError(
            f"ASSET_FORMAT_UNSUPPORTED asset={asset!r}; expected BASE-QUOTE, for example BTC-USDT"
        )
    return parts[0], parts[1]


def resolve_symbol(asset: str, venue: str, market_type: str) -> str:
    """Resolve BASE-QUOTE assets to public exchange symbols.

    Supported scope is explicit: Binance, OKX, Bybit, optional Coinbase
    Exchange spot, and optional Kraken spot. The mapper does not verify live exchange listings;
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
    if venue == "kraken" and market_type == "spot_usdt":
        kraken_base = "XBT" if base == "BTC" else base
        return f"{kraken_base}{quote}"
    if venue == "kraken" and market_type == "perp_usdt":
        raise SymbolMappingError("MARKET_TYPE_UNSUPPORTED venue='kraken' market_type='perp_usdt'; Kraken connector supports spot_usdt only")
    if venue == "okx" and market_type == "spot_usdt":
        return f"{base}-{quote}"
    if venue == "okx" and market_type == "perp_usdt":
        return f"{base}-{quote}-SWAP"
    raise SymbolMappingError(f"SYMBOL_MAPPING_MISSING asset={asset} venue={venue} market_type={market_type}")