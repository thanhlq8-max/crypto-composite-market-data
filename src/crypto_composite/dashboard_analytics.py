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
    grade = zone.get("evidence_grade") if isinstance(zone.get("evidence_grade"), str) else "LIMITED"
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
    grade = zone.get("evidence_grade") if isinstance(zone.get("evidence_grade"), str) else "LIMITED"
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
        focus = [item for item in focus if item]
        if focus:
            detail = " ".join(focus)
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
    grade = zone.get("evidence_grade") if isinstance(zone.get("evidence_grade"), str) else "LIMITED"
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
