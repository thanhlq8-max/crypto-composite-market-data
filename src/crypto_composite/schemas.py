from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OHLCVBar:
    venue: str
    market_type: str
    symbol: str
    timeframe: str
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume_base: float
    volume_quote: Optional[float]
    trade_count: Optional[int]
    data_quality: float


@dataclass(frozen=True)
class TradePrint:
    venue: str
    market_type: str
    symbol: str
    timestamp_ms: int
    price: float
    size_base: float
    size_quote: Optional[float]
    side: Optional[str]
    is_aggressive: Optional[bool]
    trade_id: Optional[str]
    data_quality: float


@dataclass(frozen=True)
class OrderBookSnapshot:
    venue: str
    market_type: str
    symbol: str
    timestamp_ms: int
    bids: list[tuple[float, float]]
    asks: list[tuple[float, float]]
    best_bid: float
    best_ask: float
    mid: float
    spread: float
    depth_levels: int
    data_quality: float


@dataclass(frozen=True)
class FundingSnapshot:
    venue: str
    market_type: str
    symbol: str
    timestamp_ms: int
    funding_rate: float
    next_funding_time_ms: Optional[int]
    data_quality: float


@dataclass(frozen=True)
class OpenInterestSnapshot:
    venue: str
    market_type: str
    symbol: str
    timestamp_ms: int
    open_interest_base: Optional[float]
    open_interest_quote: Optional[float]
    data_quality: float


@dataclass(frozen=True)
class DataQualityReport:
    asset: str
    venues_requested: list[str]
    venues_ok: list[str]
    venues_failed: list[str]
    market_types: list[str]
    timeframe: str
    missing_sources: list[str]
    overall_quality: float
    status: str


@dataclass(frozen=True)
class CompositeOHLCVBar:
    asset: str
    timeframe: str
    market_type: str
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    median_close: float
    vwap_close: float
    volume_base_total: float
    volume_quote_total: float
    venue_count: int
    venue_weights: dict[str, float]
    coverage: float
    price_dispersion_pct: float
    data_quality: float
    is_closed: bool = True


@dataclass(frozen=True)
class CompositeOHLCVContext:
    asset: str
    timeframe: str
    generated_at_ms: int
    expected_venues: list[str]
    bars_by_market_type: dict[str, list[CompositeOHLCVBar]]
    latest_by_market_type: dict[str, CompositeOHLCVBar | None]
    status_by_market_type: dict[str, str]
    coverage_by_market_type: dict[str, float]
    notes: list[str]


@dataclass(frozen=True)
class CompositeLadderLevel:
    side: str
    price_low: float
    price_high: float
    price_mid: float
    depth_quote: float
    venue_count: int
    venue_depth_quote: dict[str, float]
    hhi: float
    persistence: float
    spoof_risk_proxy: float
    vacuum_score: float


@dataclass(frozen=True)
class CompositeOrderBookLadder:
    asset: str
    market_type: str
    generated_at_ms: int
    reference_price: float
    bucket_size: float
    expected_venues: list[str]
    venue_count: int
    coverage: float
    bid_levels: list[CompositeLadderLevel]
    ask_levels: list[CompositeLadderLevel]
    top_bid_wall: CompositeLadderLevel | None
    top_ask_wall: CompositeLadderLevel | None
    bid_depth_total: float
    ask_depth_total: float
    depth_imbalance: float
    status: str
    notes: list[str]
