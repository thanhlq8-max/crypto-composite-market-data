from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crypto_composite.dashboard_profile import read_dashboard_profile
from crypto_composite.lfx_alignment import build_lfx_alignment


EVIDENCE_METHOD = {
    "CORROBORATED": (
        "Book status is OK, at least two venues contribute, and no venue supplies a majority of bucket depth."
    ),
    "CONCENTRATED": "One venue supplies more than half of the observed bucket depth.",
    "LIMITED": "Book coverage is partial/weak or fewer than two venues contribute to the bucket.",
}


def _read_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else None


def _asset_roots(root: Path) -> list[tuple[str | None, Path]]:
    universe = _read_object(root / "universe_summary.json")
    if universe is None:
        return [(None, root)]

    results = universe.get("asset_results")
    if not isinstance(results, dict):
        return []

    resolved: list[tuple[str | None, Path]] = []
    for asset, result in sorted(results.items()):
        if not isinstance(result, dict) or not isinstance(result.get("artifact_dir"), str):
            continue
        candidate = (root / result["artifact_dir"]).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.is_dir():
            resolved.append((str(asset), candidate))
    return resolved


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number == number and number not in (float("inf"), float("-inf")) else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _ordered_timeframes(keys: set[str], requested: list[str], primary: str | None) -> list[str]:
    ordered: list[str] = []
    if primary in keys:
        ordered.append(primary)
    for timeframe in requested:
        if timeframe in keys and timeframe not in ordered:
            ordered.append(timeframe)
    for timeframe in sorted(keys):
        if timeframe not in ordered:
            ordered.append(timeframe)
    return ordered


def _venue_majority_share(level: dict[str, Any]) -> float | None:
    venue_depth = level.get("venue_depth_quote")
    if not isinstance(venue_depth, dict):
        return None
    values = [number for value in venue_depth.values() if (number := _finite_number(value)) is not None and number > 0]
    total = sum(values)
    return max(values) / total if values and total > 0 else None


def _evidence_grade(level: dict[str, Any], ladder: dict[str, Any]) -> tuple[str, float | None]:
    venue_count = level.get("venue_count")
    majority_share = _venue_majority_share(level)
    if ladder.get("status") != "COMPOSITE_BOOK_OK" or not isinstance(venue_count, int) or venue_count < 2:
        return "LIMITED", majority_share
    if majority_share is None or majority_share > 0.5:
        return "CONCENTRATED", majority_share
    return "CORROBORATED", majority_share


def _zone_reference_context(level: dict[str, Any], ladder: dict[str, Any]) -> tuple[str | None, float | None]:
    reference = _finite_number(ladder.get("reference_price"))
    low = _finite_number(level.get("price_low"))
    high = _finite_number(level.get("price_high"))
    if reference is None or reference <= 0 or low is None or high is None:
        return None, None
    low, high = min(low, high), max(low, high)
    if high < reference:
        return "BELOW_REFERENCE", round((reference - high) / reference * 100.0, 6)
    if low > reference:
        return "ABOVE_REFERENCE", round((low - reference) / reference * 100.0, 6)
    return "CONTAINS_REFERENCE", 0.0


def _lfx_zone_role(kind: Any) -> tuple[str, str, str]:
    if kind in {"BID_LIQUIDITY_CONCENTRATION", "ASK_LIQUIDITY_CONCENTRATION"}:
        return (
            "PUBLIC_DEPTH_CONCENTRATION_REF",
            "Concentration reference",
            "Track depth quote, venue mix, HHI, and persistence proxy after refresh.",
        )
    if kind in {"BID_PUBLIC_DEPTH_VACUUM", "ASK_PUBLIC_DEPTH_VACUUM"}:
        return (
            "PUBLIC_DEPTH_VACUUM_REF",
            "Vacuum reference",
            "Track whether the low-depth bucket remains thin or gets refilled after refresh.",
        )
    return (
        "PUBLIC_DEPTH_CONTEXT_REF",
        "Public-depth reference",
        "Track public artifact fields after refresh.",
    )


def _review_value(grade: Any) -> str:
    if grade == "CORROBORATED":
        return "CORROBORATED_REFERENCE"
    if grade == "CONCENTRATED":
        return "CONCENTRATED_REFERENCE"
    return "LIMITED_REFERENCE"


def _lfx_zone_review(zone: dict[str, Any]) -> dict[str, Any]:
    role, role_label, refresh_check = _lfx_zone_role(zone.get("kind"))
    relation = zone.get("reference_relation")
    distance = _finite_number(zone.get("distance_to_reference_pct"))
    evidence_grade = zone.get("evidence_grade")
    grade = evidence_grade if isinstance(evidence_grade, str) else "LIMITED"
    return {
        "status": "PUBLIC_ARTIFACT_REVIEW_ONLY",
        "role": role,
        "role_label": role_label,
        "review_value": _review_value(grade),
        "proximity": {
            "reference_relation": relation,
            "distance_to_reference_pct": distance,
            "description": _relation_text(relation),
        },
        "density_context": (
            "Density/confluence reference only; this does not create a route, target, or signal."
        ),
        "counterflow_check": (
            "On the next artifact refresh, compare opposite-side concentration, depth imbalance, "
            "venue mix, and persistence proxy before changing the review note."
        ),
        "refresh_check": refresh_check,
        "quality_note": EVIDENCE_METHOD.get(grade, EVIDENCE_METHOD["LIMITED"]),
        "boundary": (
            "Zone review text is descriptive public-depth context only; no support/resistance, "
            "hidden-liquidity, private-flow, route, target, or future-reaction claim."
        ),
    }


def _zone(level: dict[str, Any], ladder: dict[str, Any], kind: str, label: str) -> dict[str, Any]:
    grade, majority_share = _evidence_grade(level, ladder)
    reference_relation, distance_to_reference_pct = _zone_reference_context(level, ladder)
    zone = {
        "kind": kind,
        "label": label,
        "side": level.get("side"),
        "price_low": level.get("price_low"),
        "price_high": level.get("price_high"),
        "price_mid": level.get("price_mid"),
        "depth_quote": level.get("depth_quote"),
        "venue_count": level.get("venue_count"),
        "venue_majority_share": majority_share,
        "hhi": level.get("hhi"),
        "persistence_proxy": level.get("persistence"),
        "spoof_risk_proxy": level.get("spoof_risk_proxy"),
        "vacuum_score": level.get("vacuum_score"),
        "reference_relation": reference_relation,
        "distance_to_reference_pct": distance_to_reference_pct,
        "evidence_grade": grade,
        "evidence_definition": EVIDENCE_METHOD[grade],
    }
    zone["lfx_zone_review"] = _lfx_zone_review(zone)
    return zone


def _vacuum_level(levels: Any, excluded: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(levels, list):
        return None
    candidates = [
        level
        for level in levels
        if isinstance(level, dict) and _finite_number(level.get("vacuum_score")) is not None
    ]
    if excluded is not None:
        candidates = [
            level
            for level in candidates
            if (level.get("price_low"), level.get("price_high"))
            != (excluded.get("price_low"), excluded.get("price_high"))
        ]
    return max(candidates, key=lambda level: float(level["vacuum_score"]), default=None)


def _observed_zones(ladder: dict[str, Any] | None) -> list[dict[str, Any]]:
    if ladder is None:
        return []
    zones: list[dict[str, Any]] = []
    for side, field, levels_field in (
        ("Bid", "top_bid_wall", "bid_levels"),
        ("Ask", "top_ask_wall", "ask_levels"),
    ):
        wall = ladder.get(field)
        wall = wall if isinstance(wall, dict) else None
        if wall is not None:
            zones.append(
                _zone(
                    wall,
                    ladder,
                    f"{side.upper()}_LIQUIDITY_CONCENTRATION",
                    f"{side} liquidity concentration",
                )
            )
        vacuum = _vacuum_level(ladder.get(levels_field), wall)
        if vacuum is not None:
            zones.append(
                _zone(vacuum, ladder, f"{side.upper()}_PUBLIC_DEPTH_VACUUM", f"{side} public-depth vacuum")
            )
    return zones


PRICE_ZONE_MAP_DISCLAIMER = (
    "Observed public market data. Reaction bands count historical closed-bar swing reversals in "
    "the loaded window; depth zones describe the current public snapshot. Descriptive context "
    "only — not investment advice, a prediction, or an execution instruction."
)

REACTION_ZONE_TOLERANCE_PCT = 0.2
REACTION_ZONE_MIN_TOUCHES = 2
REACTION_ZONE_MAX_ZONES = 6
_SWING_WINDOW = 2


def _closed_bars(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [bar for bar in bars if isinstance(bar, dict) and bar.get("is_closed", True)]


def _swing_points(bars: list[dict[str, Any]], k: int = _SWING_WINDOW) -> list[dict[str, Any]]:
    """Local high/low extrema of closed composite bars (±k-bar neighborhood)."""
    points: list[dict[str, Any]] = []
    if len(bars) < 2 * k + 1:
        return points
    for i in range(k, len(bars) - k):
        window = bars[i - k : i + k + 1]
        highs = [_finite_number(bar.get("high")) for bar in window]
        lows = [_finite_number(bar.get("low")) for bar in window]
        ts = bars[i].get("timestamp_ms")
        if all(value is not None for value in highs) and highs[k] == max(v for v in highs if v is not None):
            points.append({"price": highs[k], "timestamp_ms": ts, "kind": "swing_high"})
        if all(value is not None for value in lows) and lows[k] == min(v for v in lows if v is not None):
            points.append({"price": lows[k], "timestamp_ms": ts, "kind": "swing_low"})
    return points


def _reaction_zones(
    bars: list[dict[str, Any]],
    reference_price: float | None,
    tolerance_pct: float = REACTION_ZONE_TOLERANCE_PCT,
    min_touches: int = REACTION_ZONE_MIN_TOUCHES,
    max_zones: int = REACTION_ZONE_MAX_ZONES,
) -> list[dict[str, Any]]:
    """Cluster closed-bar swing extrema into historical price reaction bands.

    Purely descriptive: a band records where and how often closed composite
    bars reversed inside the loaded window. It makes no claim about future
    behavior (D10 display-layer wording; core artifacts stay unchanged).
    """
    closed = _closed_bars(bars)
    points = sorted(_swing_points(closed), key=lambda p: p["price"])
    if not points:
        return []
    anchor = reference_price if reference_price and reference_price > 0 else points[len(points) // 2]["price"]
    tolerance = anchor * tolerance_pct / 100.0
    clusters: list[list[dict[str, Any]]] = []
    for point in points:
        if clusters and point["price"] - clusters[-1][0]["price"] <= tolerance:
            clusters[-1].append(point)
        else:
            clusters.append([point])
    zones: list[dict[str, Any]] = []
    for cluster in clusters:
        if len(cluster) < min_touches:
            continue
        prices = [point["price"] for point in cluster]
        stamps = [point["timestamp_ms"] for point in cluster if point["timestamp_ms"] is not None]
        low, high = min(prices), max(prices)
        mid = (low + high) / 2
        relation = None
        distance_pct = None
        if reference_price and reference_price > 0:
            if high < reference_price:
                relation = "BELOW_REFERENCE"
                distance_pct = round((reference_price - high) / reference_price * 100.0, 6)
            elif low > reference_price:
                relation = "ABOVE_REFERENCE"
                distance_pct = round((low - reference_price) / reference_price * 100.0, 6)
            else:
                relation = "CONTAINS_REFERENCE"
                distance_pct = 0.0
        zones.append(
            {
                "kind": "PRICE_REACTION_BAND",
                "label": "Price reaction band",
                "price_low": round(low, 8),
                "price_high": round(high, 8),
                "price_mid": round(mid, 8),
                "touch_count": len(cluster),
                "swing_high_count": sum(1 for point in cluster if point["kind"] == "swing_high"),
                "swing_low_count": sum(1 for point in cluster if point["kind"] == "swing_low"),
                "first_touch_ms": min(stamps) if stamps else None,
                "last_touch_ms": max(stamps) if stamps else None,
                "reference_relation": relation,
                "distance_to_reference_pct": distance_pct,
                "basis": (
                    f"closed-bar swing extrema clustered within {tolerance_pct}% of reference; "
                    "historical description of the loaded window only"
                ),
            }
        )
    zones.sort(key=lambda zone: (zone["distance_to_reference_pct"] is None, zone["distance_to_reference_pct"], -zone["touch_count"]))
    return zones[:max_zones]


def _previous_closed_bar_delta(bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    closed = _closed_bars(bars)
    if len(closed) < 2:
        return None
    latest, previous = closed[-1], closed[-2]
    latest_close = _finite_number(latest.get("close"))
    previous_close = _finite_number(previous.get("close"))
    latest_quote = _finite_number(latest.get("volume_quote_total"))
    previous_quote = _finite_number(previous.get("volume_quote_total"))
    return {
        "close_change_pct": (
            round((latest_close - previous_close) / previous_close * 100.0, 6)
            if latest_close is not None and previous_close is not None and previous_close > 0
            else None
        ),
        "volume_quote_change_pct": (
            round((latest_quote - previous_quote) / previous_quote * 100.0, 6)
            if latest_quote is not None and previous_quote is not None and previous_quote > 0
            else None
        ),
        "venue_count_previous": previous.get("venue_count"),
        "venue_count_latest": latest.get("venue_count"),
        "timestamp_ms_latest": latest.get("timestamp_ms"),
    }


def _price_text(value: Any) -> str:
    number = _finite_number(value)
    if number is None:
        return "unavailable"
    digits = 5 if abs(number) < 10 else 2
    return f"{number:,.{digits}f}"


def _zone_map_insights(
    market_type: str,
    status: Any,
    latest: dict[str, Any] | None,
    bars: list[dict[str, Any]],
    ladder: dict[str, Any] | None,
    liquidity_zones: list[dict[str, Any]],
    reaction_zones: list[dict[str, Any]],
    delta: dict[str, Any] | None,
) -> list[str]:
    lines: list[str] = []
    closed = _closed_bars(bars)
    status_bar = closed[-1] if closed else latest
    if latest is not None:
        head = f"{market_type}: composite close {_price_text(latest.get('close'))}"
        if isinstance(status, str):
            head += f"; status {status}"
        if status_bar is not None:
            coverage = _finite_number(status_bar.get("coverage"))
            dispersion = _finite_number(status_bar.get("price_dispersion_pct"))
            if coverage is not None and dispersion is not None:
                head += f" (coverage {coverage:.2f}, dispersion {dispersion:.4f}% on last closed bar)"
        lines.append(head + ".")
    for zone in reaction_zones[:2]:
        lines.append(
            f"Price reacted {zone['touch_count']} times in "
            f"{_price_text(zone['price_low'])}-{_price_text(zone['price_high'])} during the loaded window "
            f"({zone['swing_high_count']} swing highs / {zone['swing_low_count']} swing lows)."
        )
    top_wall = next((zone for zone in liquidity_zones if "LIQUIDITY_CONCENTRATION" in str(zone.get("kind"))), None)
    if top_wall is not None:
        lines.append(
            f"Deepest {str(top_wall.get('side') or '').lower()} concentration "
            f"{_price_text(top_wall.get('price_low'))}-{_price_text(top_wall.get('price_high'))} holds "
            f"{_price_text(top_wall.get('depth_quote'))} quote across {top_wall.get('venue_count')} venue(s)."
        )
    if ladder is not None:
        imbalance = _finite_number(ladder.get("depth_imbalance"))
        if imbalance is not None:
            lines.append(f"Depth imbalance {imbalance:+.3f} between bid and ask buckets near reference.")
    if delta is not None and delta.get("close_change_pct") is not None:
        line = f"Last closed bar moved {delta['close_change_pct']:+.4f}% vs the prior closed bar"
        if delta.get("venue_count_previous") != delta.get("venue_count_latest"):
            line += f"; venue count {delta.get('venue_count_previous')} -> {delta.get('venue_count_latest')}"
        lines.append(line + ".")
    return lines


def _price_zone_map(
    timeframe: str,
    market_type: str,
    bars: list[dict[str, Any]],
    latest: dict[str, Any] | None,
    status: Any,
    ladder: dict[str, Any] | None,
    liquidity_zones: list[dict[str, Any]],
) -> dict[str, Any]:
    """Per-market price map: reaction bands, depth zones, and reference levels."""
    reference = None
    if ladder is not None:
        reference = _finite_number(ladder.get("reference_price"))
    if (reference is None or reference <= 0) and latest is not None:
        reference = _finite_number(latest.get("close"))
    closed = _closed_bars(bars)
    window_lows_raw = [_finite_number(bar.get("low")) for bar in closed]
    window_highs_raw = [_finite_number(bar.get("high")) for bar in closed]
    window_lows = [value for value in window_lows_raw if value is not None]
    window_highs = [value for value in window_highs_raw if value is not None]
    reaction = _reaction_zones(bars, reference)
    delta = _previous_closed_bar_delta(bars)
    return {
        "timeframe": timeframe,
        "market_type": market_type,
        "reference_price": reference,
        "window": {
            "closed_bar_count": len(closed),
            "price_low": min(window_lows) if window_lows else None,
            "price_high": max(window_highs) if window_highs else None,
        },
        "reaction_zones": reaction,
        "liquidity_zones": liquidity_zones,
        "previous_closed_bar_delta": delta,
        "insights": _zone_map_insights(
            market_type, status, latest, bars, ladder, liquidity_zones, reaction, delta
        ),
        "disclaimer": PRICE_ZONE_MAP_DISCLAIMER,
    }


def _dislocation(markets: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest = {market.get("market_type"): market.get("latest_bar") for market in markets}
    spot = latest.get("spot_usdt")
    perp = latest.get("perp_usdt")
    if not isinstance(spot, dict) or not isinstance(perp, dict):
        return None
    spot_close = _finite_number(spot.get("close"))
    perp_close = _finite_number(perp.get("close"))
    if spot_close is None or perp_close is None or spot_close <= 0:
        return None
    return {
        "kind": "SPOT_PERP_DISLOCATION_BAND",
        "price_low": min(spot_close, perp_close),
        "price_high": max(spot_close, perp_close),
        "spot_close": spot_close,
        "perp_close": perp_close,
        "basis_pct": (perp_close - spot_close) / spot_close * 100.0,
        "interpretation": "Observed composite close difference; not a convergence forecast.",
    }


def _nearest_concentration(zones: list[dict[str, Any]], side: str) -> dict[str, Any] | None:
    kind = f"{side.upper()}_LIQUIDITY_CONCENTRATION"
    candidates = [
        zone
        for zone in zones
        if zone.get("kind") == kind and _finite_number(zone.get("distance_to_reference_pct")) is not None
    ]
    return min(candidates, key=lambda zone: float(zone["distance_to_reference_pct"]), default=None)


def _relation_text(value: Any) -> str:
    if value == "BELOW_REFERENCE":
        return "below reference"
    if value == "ABOVE_REFERENCE":
        return "above reference"
    if value == "CONTAINS_REFERENCE":
        return "at reference"
    return "near reference"


def _zone_focus_text(zone: dict[str, Any] | None, label: str) -> str | None:
    if zone is None:
        return None
    distance = _finite_number(zone.get("distance_to_reference_pct"))
    distance_text = f"{distance:.3f}% " if distance is not None else ""
    evidence_grade = zone.get("evidence_grade")
    grade = evidence_grade if isinstance(evidence_grade, str) else "LIMITED"
    return f"{label} {distance_text}{_relation_text(zone.get('reference_relation'))} ({grade})."


def _zone_readout(zones: list[dict[str, Any]], monitoring_brief: dict[str, Any]) -> dict[str, Any]:
    confidence = monitoring_brief.get("confidence_risk")
    confidence = confidence if isinstance(confidence, dict) else {}
    grade_counts = confidence.get("evidence_grade_counts")
    grade_counts = grade_counts if isinstance(grade_counts, dict) else {}
    total = len(zones)
    corroborated = int(grade_counts.get("CORROBORATED", 0) or 0)
    limited = int(grade_counts.get("LIMITED", 0) or 0)
    now = monitoring_brief.get("now")
    now = now if isinstance(now, dict) else {}
    next_check = monitoring_brief.get("next_evidence_check")
    next_check = next_check if isinstance(next_check, dict) else {}

    if total == 0:
        title = "No practical public-depth zones"
        detail = "Generate or refresh a composite orderbook ladder before comparing concentration and vacuum ranges."
    else:
        title = f"{corroborated}/{total} zones corroborated"
        focus = [
            _zone_focus_text(now.get("nearest_bid_concentration"), "Nearest bid concentration"),
            _zone_focus_text(now.get("nearest_ask_concentration"), "Nearest ask concentration"),
        ]
        focus_texts = [item for item in focus if item]
        if focus_texts:
            detail = " ".join(focus_texts)
        else:
            detail = "Observed zones exist, but no nearest bid/ask concentration range has enough context."
        if limited:
            detail = f"{detail} {limited} limited zone(s) need stronger venue coverage before interpretation."

    return {
        "title": title,
        "detail": detail,
        "next_check": next_check.get("observe") or "Refresh artifacts before comparing zone evidence.",
        "limitation": confidence.get("snapshot_limit")
        or "Single generated snapshot; no future-reaction or hidden-liquidity inference.",
        "evidence_mix": {
            "total_zones": total,
            "corroborated": corroborated,
            "concentrated": int(grade_counts.get("CONCENTRATED", 0) or 0),
            "limited": limited,
        },
    }


def _ratio_pct_text(value: Any) -> str:
    number = _finite_number(value)
    return "unavailable" if number is None else f"{number * 100:+.3f}%"


def _value_pct_text(value: Any) -> str:
    number = _finite_number(value)
    return "unavailable" if number is None else f"{number:.4f}%"


def _number_text(value: Any, digits: int = 2) -> str:
    number = _finite_number(value)
    return "unavailable" if number is None else f"{number:.{digits}f}"


def _zone_range_text(zone: dict[str, Any] | None) -> str:
    if zone is None:
        return "unavailable"
    low = _finite_number(zone.get("price_low"))
    high = _finite_number(zone.get("price_high"))
    if low is None or high is None:
        price_text = "range unavailable"
    else:
        price_text = f"{low:.2f} - {high:.2f}"
    distance = _finite_number(zone.get("distance_to_reference_pct"))
    distance_text = (
        f"{distance:.3f}% {_relation_text(zone.get('reference_relation'))}"
        if distance is not None
        else "distance unavailable"
    )
    evidence_grade = zone.get("evidence_grade")
    grade = evidence_grade if isinstance(evidence_grade, str) else "LIMITED"
    return f"{price_text}; {distance_text}; {grade}"


def _mission_row(panel: str, title: str, detail: str, basis: list[str]) -> dict[str, Any]:
    return {
        "panel": panel,
        "title": title,
        "detail": detail,
        "artifact_basis": basis,
    }


def _next_scenario_title(kind: Any) -> str:
    if kind == "RESTORE_OHLCV_COVERAGE":
        return "Restore OHLCV coverage"
    if kind == "GENERATE_BOOK_CONTEXT":
        return "Generate public book context"
    if kind == "RESTORE_BOOK_COVERAGE":
        return "Restore public book coverage"
    if kind == "REFRESH_ZONE_EVIDENCE":
        return "Compare zone evidence after refresh"
    if kind == "REFRESH_BOOK_CONTEXT":
        return "Check for practical depth context"
    return "Evidence check unavailable"


def _lfx_mission_control(monitoring_brief: dict[str, Any], zone_readout: dict[str, Any]) -> dict[str, Any]:
    """Build adapted LFX-2 v8.1-D display rows from public artifact evidence."""
    past = monitoring_brief.get("past")
    past = past if isinstance(past, dict) else {}
    now = monitoring_brief.get("now")
    now = now if isinstance(now, dict) else {}
    book = now.get("book")
    book = book if isinstance(book, dict) else {}
    next_check = monitoring_brief.get("next_evidence_check")
    next_check = next_check if isinstance(next_check, dict) else {}
    confidence = monitoring_brief.get("confidence_risk")
    confidence = confidence if isinstance(confidence, dict) else {}
    evidence_mix = zone_readout.get("evidence_mix")
    evidence_mix = evidence_mix if isinstance(evidence_mix, dict) else {}
    total_zones = int(evidence_mix.get("total_zones", 0) or 0)
    corroborated = int(evidence_mix.get("corroborated", 0) or 0)
    bid = now.get("nearest_bid_concentration")
    bid = bid if isinstance(bid, dict) else None
    ask = now.get("nearest_ask_concentration")
    ask = ask if isinstance(ask, dict) else None
    kind = next_check.get("kind")

    if kind in {"RESTORE_OHLCV_COVERAGE", "RESTORE_BOOK_COVERAGE"}:
        mission_title = "Restore public-data coverage"
        trader_title = "VERIFY DATA"
    elif kind == "GENERATE_BOOK_CONTEXT":
        mission_title = "Generate public-depth context"
        trader_title = "VERIFY DATA"
    elif bid is not None and ask is not None:
        mission_title = "Compare both-side concentration ranges"
        trader_title = "OBSERVE PUBLIC ZONES"
    elif bid is not None or ask is not None:
        mission_title = "Review available concentration side"
        trader_title = "OBSERVE PUBLIC ZONES"
    else:
        mission_title = "Wait for practical depth evidence"
        trader_title = "WAIT FOR REFRESH"

    timeframe = past.get("timeframe") if isinstance(past.get("timeframe"), str) else "timeframe unavailable"
    bar_count = past.get("bar_count")
    close_change = _finite_number(past.get("close_change_pct"))
    if close_change is None:
        did_title = "Composite history unavailable"
    else:
        did_title = f"Composite close {close_change:+.3f}%"

    focus_parts = [
        f"Bid {_zone_range_text(bid)}" if bid is not None else None,
        f"Ask {_zone_range_text(ask)}" if ask is not None else None,
    ]
    focus_text = "; ".join(item for item in focus_parts if item) or "nearest concentration unavailable"
    book_status = book.get("status") or "book status unavailable"
    depth_detail = (
        f"{book_status}; coverage {_ratio_pct_text(book.get('coverage'))}; "
        f"depth bid {_number_text(book.get('bid_depth_total'), 0)} vs "
        f"ask {_number_text(book.get('ask_depth_total'), 0)}; "
        f"imbalance {_ratio_pct_text(book.get('depth_imbalance'))}; dispersion {_value_pct_text(now.get('price_dispersion_pct'))}."
    )
    status_title = " / ".join(
        str(item) for item in [confidence.get("ohlcv_status"), confidence.get("book_status")] if item
    )
    if not status_title:
        status_title = "Quality unavailable"

    rows = [
        _mission_row(
            "MM Mission",
            mission_title,
            (
                f"{next_check.get('observe') or 'Refresh artifacts before comparing public-depth evidence.'} "
                "Adapted mission-control text uses public artifacts only."
            ),
            ["next_evidence_check", "zone_readout", "book_status"],
        ),
        _mission_row(
            "TRADER Mode",
            trader_title,
            "Review artifact evidence and quality gates only; no execution guidance.",
            ["ohlcv_status", "book_status", "observed_zones"],
        ),
        _mission_row(
            "NEXT Scenario",
            _next_scenario_title(kind),
            next_check.get("observe") or "Refresh artifacts before comparing zone evidence.",
            ["next_evidence_check", "refresh_profile"],
        ),
        _mission_row(
            "DID / Past",
            did_title,
            f"{timeframe} artifact contains {bar_count if isinstance(bar_count, int) else 'unavailable'} composite bars.",
            ["latest_two_composite_bars", "close_change_pct"],
        ),
        _mission_row(
            "DOING / Now",
            focus_text,
            depth_detail,
            ["latest_bar", "public_orderbook_ladder", "nearest_concentration"],
        ),
        _mission_row(
            "KEY Zones",
            str(zone_readout.get("title") or "Zone readout unavailable"),
            str(zone_readout.get("detail") or "Generate or refresh public-depth artifacts before review."),
            ["observed_zones", "evidence_mix", "distance_to_reference"],
        ),
        _mission_row(
            "INV / Release",
            f"Public depth imbalance {_ratio_pct_text(book.get('depth_imbalance'))}",
            (
                f"Bid {_zone_range_text(bid)}; ask {_zone_range_text(ask)}. "
                "This is a public-depth proxy only; no real inventory or release claim."
            ),
            ["depth_imbalance", "nearest_concentration", "price_dispersion"],
        ),
        _mission_row(
            "Confidence / Risk",
            status_title,
            (
                f"Book coverage {_ratio_pct_text(confidence.get('book_coverage'))}; "
                f"{corroborated}/{total_zones} zones corroborated. "
                f"{confidence.get('snapshot_limit') or 'Single generated snapshot only.'}"
            ),
            ["coverage", "venue_count", "evidence_grade_counts", "snapshot_limit"],
        ),
    ]
    return {
        "status": "ADAPTED_MONITOR_ONLY",
        "rows": rows,
        "boundary": (
            "Mission-control rows are adapted display text over generated public artifacts only; "
            "no signal, ranking, prediction, execution, or private-flow claim."
        ),
    }


def _zone_map_focus(zone: dict[str, Any] | None) -> dict[str, Any] | None:
    if zone is None:
        return None
    grade = zone.get("evidence_grade") if isinstance(zone.get("evidence_grade"), str) else None
    relation = zone.get("reference_relation") if isinstance(zone.get("reference_relation"), str) else None
    distance = _finite_number(zone.get("distance_to_reference_pct"))
    relation_text = _relation_text(relation)
    distance_text = f"{distance:.3f}% {relation_text}" if distance is not None else relation_text
    return {
        "price_low": zone.get("price_low"),
        "price_high": zone.get("price_high"),
        "reference_relation": relation,
        "distance_to_reference_pct": distance,
        "evidence_grade": grade,
        "summary": f"{distance_text} / {grade}" if grade else distance_text,
    }


def _mtf_zone_map(timeframe_rows: list[dict[str, Any]], primary_timeframe: str | None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for timeframe_row in timeframe_rows:
        timeframe = timeframe_row.get("timeframe")
        markets = timeframe_row.get("markets")
        if not isinstance(markets, list):
            continue
        for market in markets:
            if not isinstance(market, dict):
                continue
            readout = market.get("zone_readout")
            readout = readout if isinstance(readout, dict) else {}
            mix = readout.get("evidence_mix")
            mix = mix if isinstance(mix, dict) else {}
            brief = market.get("monitoring_brief")
            brief = brief if isinstance(brief, dict) else {}
            now = brief.get("now")
            now = now if isinstance(now, dict) else {}
            rows.append(
                {
                    "timeframe": timeframe,
                    "market_type": market.get("market_type"),
                    "is_primary": timeframe == primary_timeframe,
                    "zone_count": mix.get("total_zones"),
                    "corroborated": mix.get("corroborated"),
                    "concentrated": mix.get("concentrated"),
                    "limited": mix.get("limited"),
                    "nearest_bid": _zone_map_focus(now.get("nearest_bid_concentration")),
                    "nearest_ask": _zone_map_focus(now.get("nearest_ask_concentration")),
                    "next_check": readout.get("next_check"),
                }
            )
    return {
        "primary_timeframe": primary_timeframe,
        "timeframe_count": len(timeframe_rows),
        "rows": rows,
        "boundary": (
            "Cross-timeframe map is descriptive public-artifact context only; no signal, ranking, "
            "prediction, or execution instruction."
        ),
    }


def _monitoring_brief(
    timeframe: str,
    bars: list[dict[str, Any]],
    latest: dict[str, Any] | None,
    ohlcv_status: Any,
    ladder: dict[str, Any] | None,
    zones: list[dict[str, Any]],
) -> dict[str, Any]:
    close_change_pct = None
    if len(bars) >= 2:
        prior_close = _finite_number(bars[-2].get("close"))
        current_close = _finite_number(bars[-1].get("close"))
        if prior_close is not None and current_close is not None and prior_close != 0:
            close_change_pct = round((current_close - prior_close) / prior_close * 100.0, 6)

    latest = latest if isinstance(latest, dict) else None
    grade_counts = {grade: 0 for grade in EVIDENCE_METHOD}
    for zone in zones:
        grade = zone.get("evidence_grade")
        if grade in grade_counts:
            grade_counts[grade] += 1

    book = (
        {
            "status": ladder.get("status"),
            "reference_price": ladder.get("reference_price"),
            "coverage": ladder.get("coverage"),
            "venue_count": ladder.get("venue_count"),
            "bid_depth_total": ladder.get("bid_depth_total"),
            "ask_depth_total": ladder.get("ask_depth_total"),
            "depth_imbalance": ladder.get("depth_imbalance"),
        }
        if ladder is not None
        else None
    )
    nearest_bid = _nearest_concentration(zones, "bid")
    nearest_ask = _nearest_concentration(zones, "ask")

    if ohlcv_status is not None and ohlcv_status != "COMPOSITE_DATA_OK":
        next_evidence_check = {
            "kind": "RESTORE_OHLCV_COVERAGE",
            "condition": "Before interpreting the latest composite price movement",
            "observe": "Refresh missing OHLCV venue data until the composite data status is OK.",
        }
    elif ladder is None:
        next_evidence_check = {
            "kind": "GENERATE_BOOK_CONTEXT",
            "condition": "After a composite orderbook artifact is generated",
            "observe": "Review venue coverage before interpreting public-depth zones.",
        }
    else:
        if ladder.get("status") != "COMPOSITE_BOOK_OK":
            next_evidence_check = {
                "kind": "RESTORE_BOOK_COVERAGE",
                "condition": "Before interpreting public-depth structure",
                "observe": "Restore or refresh venue coverage until the composite book status is OK.",
            }
        elif nearest_bid is not None or nearest_ask is not None:
            next_evidence_check = {
                "kind": "REFRESH_ZONE_EVIDENCE",
                "condition": "After the next artifact refresh",
                "observe": (
                    "Compare the nearest concentration ranges, contributing venues, majority share, and depth quote."
                ),
            }
        else:
            next_evidence_check = {
                "kind": "REFRESH_BOOK_CONTEXT",
                "condition": "After the next artifact refresh",
                "observe": "Check whether a practical multi-venue concentration range becomes available.",
            }

    return {
        "past": {
            "timeframe": timeframe,
            "bar_count": len(bars),
            "close_change_pct": close_change_pct,
        },
        "now": {
            "latest_close": latest.get("close") if latest is not None else None,
            "price_dispersion_pct": latest.get("price_dispersion_pct") if latest is not None else None,
            "ohlcv_coverage": latest.get("coverage") if latest is not None else None,
            "book": book,
            "nearest_bid_concentration": nearest_bid,
            "nearest_ask_concentration": nearest_ask,
        },
        "next_evidence_check": next_evidence_check,
        "confidence_risk": {
            "ohlcv_status": ohlcv_status,
            "book_status": ladder.get("status") if ladder is not None else None,
            "book_coverage": ladder.get("coverage") if ladder is not None else None,
            "zone_count": len(zones),
            "evidence_grade_counts": grade_counts,
            "snapshot_limit": "Single generated snapshot; no future-reaction or hidden-liquidity inference.",
        },
    }


def _build_asset(
    asset_hint: str | None,
    asset_root: Path,
    root: Path,
    profile: dict[str, Any] | None,
) -> dict[str, Any] | None:
    ohlcv_by_timeframe = _read_object(asset_root / "composite_ohlcv.json") or {}
    ladder_by_timeframe = _read_object(asset_root / "composite_orderbook_ladder.json") or {}
    quality_by_timeframe = _read_object(asset_root / "data_quality.json") or {}
    run_summary = _read_object(asset_root / "run_summary.json") or {}
    asset = asset_hint or run_summary.get("asset")
    requested_timeframes = _string_list(profile.get("timeframes") if profile is not None else None)
    if not requested_timeframes:
        requested_timeframes = _string_list(run_summary.get("timeframes"))
    primary_timeframe = profile.get("primary_timeframe") if profile is not None else None
    primary_timeframe = primary_timeframe if isinstance(primary_timeframe, str) else None
    timeframes = _ordered_timeframes(
        set(ohlcv_by_timeframe) | set(ladder_by_timeframe) | set(quality_by_timeframe),
        requested_timeframes,
        primary_timeframe,
    )
    if not timeframes:
        return None

    timeframe_rows: list[dict[str, Any]] = []
    for timeframe in timeframes:
        ohlcv = ohlcv_by_timeframe.get(timeframe)
        ohlcv = ohlcv if isinstance(ohlcv, dict) else {}
        ladders = ladder_by_timeframe.get(timeframe)
        ladders = ladders if isinstance(ladders, dict) else {}
        bars_by_market = ohlcv.get("bars_by_market_type")
        bars_by_market = bars_by_market if isinstance(bars_by_market, dict) else {}
        latest_by_market = ohlcv.get("latest_by_market_type")
        latest_by_market = latest_by_market if isinstance(latest_by_market, dict) else {}
        status_by_market = ohlcv.get("status_by_market_type")
        status_by_market = status_by_market if isinstance(status_by_market, dict) else {}
        market_names = sorted(set(bars_by_market) | set(latest_by_market) | set(ladders))
        markets: list[dict[str, Any]] = []
        for market_type in market_names:
            bars = bars_by_market.get(market_type)
            bars = [bar for bar in bars if isinstance(bar, dict)] if isinstance(bars, list) else []
            latest = latest_by_market.get(market_type)
            latest = latest if isinstance(latest, dict) else (bars[-1] if bars else None)
            ladder = ladders.get(market_type)
            ladder = ladder if isinstance(ladder, dict) else None
            zones = _observed_zones(ladder)
            monitoring_brief = _monitoring_brief(
                timeframe,
                bars,
                latest,
                status_by_market.get(market_type),
                ladder,
                zones,
            )
            zone_readout = _zone_readout(zones, monitoring_brief)
            markets.append(
                {
                    "market_type": market_type,
                    "generated_at_ms": (
                        ladder.get("generated_at_ms") if ladder is not None else ohlcv.get("generated_at_ms")
                    ),
                    "ohlcv_status": status_by_market.get(market_type),
                    "bars": bars,
                    "latest_bar": latest,
                    "orderbook": ladder,
                    "observed_zones": zones,
                    "monitoring_brief": monitoring_brief,
                    "zone_readout": zone_readout,
                    "lfx_mission_control": _lfx_mission_control(monitoring_brief, zone_readout),
                    "price_zone_map": _price_zone_map(
                        timeframe,
                        market_type,
                        bars,
                        latest,
                        status_by_market.get(market_type),
                        ladder,
                        zones,
                    ),
                }
            )
        quality = quality_by_timeframe.get(timeframe)
        quality = quality if isinstance(quality, dict) else None
        timeframe_rows.append(
            {
                "timeframe": timeframe,
                "quality": quality,
                "source_note": quality.get("note") if quality is not None and isinstance(quality.get("note"), str) else None,
                "markets": markets,
                "spot_perp_dislocation": _dislocation(markets),
            }
        )
    return {
        "asset": asset,
        "artifact_path": str(asset_root.relative_to(root)).replace("\\", "/") or ".",
        "timeframes": timeframe_rows,
        "mtf_zone_map": _mtf_zone_map(timeframe_rows, primary_timeframe),
    }


def build_dashboard_snapshot(artifact_root: str | Path) -> dict[str, Any]:
    """Build a read-only, artifact-derived view for Dashboard V3."""
    root = Path(artifact_root).expanduser().resolve()
    profile = read_dashboard_profile(root)
    assets = [
        asset
        for hint, path in _asset_roots(root)
        if (asset := _build_asset(hint, path, root, profile)) is not None
    ]
    return {
        "mode": "OBSERVED_PUBLIC_DATA",
        "profile": profile,
        "lfx_alignment": build_lfx_alignment(profile),
        "assets": assets,
        "methodology": {
            "zone_selection": (
                "Top depth bucket and maximum vacuum-score bucket per side; exact duplicate ranges are omitted."
            ),
            "evidence_grades": EVIDENCE_METHOD,
            "snapshot_limit": (
                "Zones describe generated public snapshots. Persistence is an engine proxy, not multi-snapshot "
                "lifecycle proof."
            ),
            "cross_venue_limit": (
                "Price dispersion is shown as a metric; exact disagreement bands are unavailable without per-venue "
                "price bounds in the composite artifact."
            ),
        },
        "boundaries": [
            "Observed public-data context only.",
            "No trading signal, prediction, entry, exit, position sizing, or execution instruction.",
            "No hidden-liquidity, market-maker intent, or future price-reaction claim.",
        ],
    }
