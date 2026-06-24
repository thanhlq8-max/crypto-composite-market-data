from __future__ import annotations

import json
import os
import re
from html import escape
from pathlib import Path
from typing import Any

from crypto_composite.artifact_quality import score_artifact_root

NO_SIGNAL_BOUNDARY = "Static artifact report only; no trading signal, execution instruction, or financial advice."

_FORBIDDEN_REPORT_TERMS = (
    "BUY",
    "SELL",
    "ENTRY",
    "STOP LOSS",
    "TAKE PROFIT",
    "TP",
    "SL",
)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _html_text(value: Any) -> str:
    if value is None:
        return ""
    return escape(str(value), quote=True)


def _json_block(value: Any) -> str:
    return escape(json.dumps(value, indent=2, sort_keys=True), quote=False)


def _rel_link(target: Path, report_file: Path) -> str:
    rel = os.path.relpath(target, start=report_file.parent)
    return Path(rel).as_posix()


def _status_class(value: Any) -> str:
    text = str(value).upper()
    if text == "OK":
        return "ok"
    if text == "WARN":
        return "warn"
    if text == "ERROR":
        return "error"
    return "neutral"


def _grade_class(value: Any) -> str:
    text = str(value).upper()
    if text in {"A", "B"}:
        return "ok"
    if text == "C":
        return "warn"
    if text in {"D", "F"}:
        return "error"
    return "neutral"


def _collect_artifact_links(root: Path, report_file: Path) -> list[dict[str, str]]:
    if not root.exists() or not root.is_dir():
        return []
    links: list[dict[str, str]] = []
    for path in sorted(root.rglob("*.json")):
        if path.is_file():
            links.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "href": _rel_link(path, report_file),
                }
            )
    return links


def _asset_rows(quality: dict[str, Any]) -> str:
    rows: list[str] = []
    asset_scores = _as_mapping(quality.get("asset_scores"))
    for asset, asset_score in sorted(asset_scores.items()):
        item = _as_mapping(asset_score)
        rows.append(
            "<tr>"
            f"<td>{_html_text(asset)}</td>"
            f"<td>{_html_text(item.get('quality_score'))}</td>"
            f"<td><span class=\"badge {_grade_class(item.get('quality_grade'))}\">{_html_text(item.get('quality_grade'))}</span></td>"
            f"<td>{_html_text(', '.join(_as_mapping(item.get('timeframes')).keys()))}</td>"
            f"<td>{_html_text(len(_as_list(item.get('warnings'))))}</td>"
            "</tr>"
        )
    if not rows:
        return "<tr><td colspan=\"5\">No asset scores available.</td></tr>"
    return "\n".join(rows)


def _timeframe_rows(quality: dict[str, Any]) -> str:
    rows: list[str] = []
    asset_scores = _as_mapping(quality.get("asset_scores"))
    for asset, asset_score in sorted(asset_scores.items()):
        item = _as_mapping(asset_score)
        timeframes = _as_mapping(item.get("timeframes"))
        for timeframe, timeframe_score in sorted(timeframes.items()):
            tf_item = _as_mapping(timeframe_score)
            components = _as_mapping(tf_item.get("components"))
            rows.append(
                "<tr>"
                f"<td>{_html_text(asset)}</td>"
                f"<td>{_html_text(timeframe)}</td>"
                f"<td>{_html_text(tf_item.get('quality_score'))}</td>"
                f"<td><span class=\"badge {_grade_class(tf_item.get('quality_grade'))}\">{_html_text(tf_item.get('quality_grade'))}</span></td>"
                f"<td>{_html_text(components.get('venue_coverage'))}</td>"
                f"<td>{_html_text(components.get('ohlcv_coverage'))}</td>"
                f"<td>{_html_text(components.get('ohlcv_status'))}</td>"
                f"<td>{_html_text(components.get('price_dispersion'))}</td>"
                f"<td>{_html_text(components.get('orderbook_coverage'))}</td>"
                f"<td>{_html_text(components.get('orderbook_status'))}</td>"
                "</tr>"
            )
    if not rows:
        return "<tr><td colspan=\"10\">No timeframe scores available.</td></tr>"
    return "\n".join(rows)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _ratio_pct(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "n/a"
    ratio = number * 100.0 if abs(number) <= 1.0 else number
    return f"{ratio:.1f}%"


def _plain_number(value: Any, digits: int = 3) -> str:
    number = _number(value)
    if number is None:
        return "n/a"
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


def _quality_lookup(quality: dict[str, Any], asset: str, timeframe: str) -> dict[str, Any]:
    asset_scores = _as_mapping(quality.get("asset_scores"))
    asset_score = _as_mapping(asset_scores.get(asset))
    timeframes = _as_mapping(asset_score.get("timeframes"))
    return _as_mapping(timeframes.get(timeframe))


def _asset_report_roots(artifact_root: Path, quality: dict[str, Any]) -> list[tuple[str, Path]]:
    asset_scores = _as_mapping(quality.get("asset_scores"))
    roots: list[tuple[str, Path]] = []
    for asset in sorted(asset_scores):
        candidate = artifact_root / asset
        roots.append((asset, candidate if candidate.exists() else artifact_root))
    if roots:
        return roots

    run_summary = _as_mapping(_read_json(artifact_root / "run_summary.json"))
    asset = str(run_summary.get("asset") or "single-asset")
    return [(asset, artifact_root)]


def _depth_balance_text(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "Depth n/a"
    if number >= 0.20:
        return f"Bid depth heavier ({number:.2f})"
    if number <= -0.20:
        return f"Ask depth heavier ({number:.2f})"
    return f"Balanced depth ({number:.2f})"


def _operational_state(
    quality_grade: Any,
    ohlcv_coverage: Any,
    ohlcv_status: Any,
    book_coverage: Any,
    book_status: Any,
    dispersion_pct: Any,
    depth_imbalance: Any,
) -> tuple[str, str, str]:
    grade = str(quality_grade or "").upper()
    ohlcv_cov = _number(ohlcv_coverage)
    book_cov = _number(book_coverage)
    dispersion = _number(dispersion_pct)
    imbalance = _number(depth_imbalance)
    ohlcv_ok = str(ohlcv_status or "").endswith("OK")
    book_ok = str(book_status or "").endswith("OK")

    if grade in {"D", "F"} or ohlcv_cov is not None and ohlcv_cov < 0.50 or not ohlcv_ok:
        return (
            "DATA WEAK",
            "VERIFY DATA",
            "Inspect missing venue coverage before using the artifact downstream.",
        )
    if book_cov is not None and book_cov < 0.50 or not book_ok:
        return (
            "BOOK WEAK",
            "VERIFY DEPTH",
            "Review public orderbook coverage before relying on ladder context.",
        )
    if dispersion is not None and dispersion >= 0.15:
        return (
            "VENUE DIVERGENCE",
            "WATCH DISPERSION",
            "Monitor whether venue prices remain dispersed across the composite set.",
        )
    if imbalance is not None and abs(imbalance) >= 0.20:
        return (
            "DEPTH IMBALANCE",
            "WATCH DEPTH",
            "Monitor whether public depth remains concentrated on one side of the ladder.",
        )
    return (
        "OBSERVATION READY",
        "OBSERVE",
        "Composite coverage is stable; review raw artifacts for detailed context.",
    )



def _format_price(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "n/a"
    return f"{number:.4f}".rstrip("0").rstrip(".")


def _format_volume(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "n/a"
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.2f}m"
    if abs(number) >= 1_000:
        return f"{number / 1_000:.2f}k"
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _bar_sequence(ohlcv_context: dict[str, Any], market_type: str) -> list[dict[str, Any]]:
    bars_by_market_type = _as_mapping(ohlcv_context.get("bars_by_market_type"))
    bars = _as_list(bars_by_market_type.get(market_type))
    return [_as_mapping(item) for item in bars]


def _latest_bar(ohlcv_context: dict[str, Any], market_type: str) -> dict[str, Any]:
    bars = _bar_sequence(ohlcv_context, market_type)
    if bars:
        return bars[-1]
    latest_by_market_type = _as_mapping(ohlcv_context.get("latest_by_market_type"))
    return _as_mapping(latest_by_market_type.get(market_type))


def _previous_bar(ohlcv_context: dict[str, Any], market_type: str) -> dict[str, Any]:
    bars = _bar_sequence(ohlcv_context, market_type)
    if len(bars) >= 2:
        return bars[-2]
    return {}


def _bar_direction_text(latest: dict[str, Any], previous: dict[str, Any]) -> str:
    close = _number(latest.get("close"))
    previous_close = _number(previous.get("close"))
    if close is None or previous_close is None:
        return "Recent composite path is not available."
    delta = close - previous_close
    if abs(delta) < 1e-12:
        return "Recent composite close is unchanged."
    verb = "advanced" if delta > 0 else "softened"
    return f"Recent composite close {verb} by {_format_price(abs(delta))}."


def _range_text(bar: dict[str, Any]) -> str:
    low = _format_price(bar.get("low"))
    high = _format_price(bar.get("high"))
    close = _format_price(bar.get("close"))
    volume = _format_volume(bar.get("volume_base_total"))
    return f"Close {close}; range {low} - {high}; volume {volume} base."


def _wall_label(wall: dict[str, Any], label: str) -> str:
    if not wall:
        return f"{label} n/a"
    price = wall.get("price_mid")
    if price is None:
        price = wall.get("price_high") if label == "Ask wall" else wall.get("price_low")
    depth = _format_volume(wall.get("depth_quote"))
    venues = wall.get("venue_count", "n/a")
    spoof = _plain_number(wall.get("spoof_risk_proxy"), 2)
    vacuum = _plain_number(wall.get("vacuum_score"), 2)
    return f"{label} {_format_price(price)} | depth {depth} quote | venues {venues} | spoof {spoof} | vacuum {vacuum}"


def _key_levels_text(ladder: dict[str, Any]) -> str:
    top_bid = _as_mapping(ladder.get("top_bid_wall"))
    top_ask = _as_mapping(ladder.get("top_ask_wall"))
    reference = _format_price(ladder.get("reference_price"))
    bid_text = _wall_label(top_bid, "Bid wall")
    ask_text = _wall_label(top_ask, "Ask wall")
    return f"Reference {reference}; {bid_text}; {ask_text}."


def _risk_context_text(
    ohlcv_coverage: Any,
    book_coverage: Any,
    dispersion_pct: Any,
    depth_imbalance: Any,
    state: str,
) -> str:
    items = [
        f"OHLCV coverage {_ratio_pct(ohlcv_coverage)}",
        f"book coverage {_ratio_pct(book_coverage)}",
        f"venue dispersion {_plain_number(dispersion_pct, 4)}%",
        f"depth imbalance {_plain_number(depth_imbalance, 3)}",
    ]
    if state != "OBSERVATION READY":
        items.append(f"context state {state}")
    return "; ".join(items) + "."


def _next_monitor_briefing(state: str, ladder: dict[str, Any], latest: dict[str, Any]) -> str:
    if state == "DATA WEAK":
        return "Verify composite coverage before using the report for monitoring."
    if state == "BOOK WEAK":
        return "Verify public ladder coverage before interpreting depth context."
    if state == "VENUE DIVERGENCE":
        return "Watch whether venue dispersion compresses or persists."
    if state == "DEPTH IMBALANCE":
        return "Watch whether public depth remains concentrated on one side."
    top_bid = _as_mapping(ladder.get("top_bid_wall"))
    top_ask = _as_mapping(ladder.get("top_ask_wall"))
    close = _number(latest.get("close"))
    bid_mid = _number(top_bid.get("price_mid"))
    ask_mid = _number(top_ask.get("price_mid"))
    if close is not None and bid_mid is not None and ask_mid is not None:
        return (
            "Monitor how composite price behaves between the nearest public bid wall "
            f"({_format_price(bid_mid)}) and ask wall ({_format_price(ask_mid)})."
        )
    return "Monitor composite coverage, dispersion, and public ladder state."


def _operational_briefing_items(artifact_root: Path, quality: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for asset, asset_root in _asset_report_roots(artifact_root, quality):
        ohlcv_by_tf = _as_mapping(_read_json(asset_root / "composite_ohlcv.json"))
        ladder_by_tf = _as_mapping(_read_json(asset_root / "composite_orderbook_ladder.json"))
        for timeframe, ohlcv_context_raw in sorted(ohlcv_by_tf.items()):
            ohlcv_context = _as_mapping(ohlcv_context_raw)
            coverage_by_market_type = _as_mapping(ohlcv_context.get("coverage_by_market_type"))
            status_by_market_type = _as_mapping(ohlcv_context.get("status_by_market_type"))
            latest_by_market_type = _as_mapping(ohlcv_context.get("latest_by_market_type"))
            ladder_for_timeframe = _as_mapping(ladder_by_tf.get(timeframe))
            market_types = sorted(set(coverage_by_market_type) | set(latest_by_market_type) | set(ladder_for_timeframe))
            if not market_types:
                market_types = ["artifact"]

            tf_quality = _quality_lookup(quality, asset, timeframe)
            tf_grade = tf_quality.get("quality_grade") or "n/a"

            for market_type in market_types:
                latest = _latest_bar(ohlcv_context, market_type)
                previous = _previous_bar(ohlcv_context, market_type)
                ladder = _as_mapping(ladder_for_timeframe.get(market_type))
                ohlcv_coverage = coverage_by_market_type.get(market_type)
                ohlcv_status = status_by_market_type.get(market_type)
                book_coverage = ladder.get("coverage")
                book_status = ladder.get("status")
                dispersion_pct = latest.get("price_dispersion_pct")
                depth_imbalance = ladder.get("depth_imbalance")
                state, operator_mode, _context_next = _operational_state(
                    tf_grade,
                    ohlcv_coverage,
                    ohlcv_status,
                    book_coverage,
                    book_status,
                    dispersion_pct,
                    depth_imbalance,
                )
                items.append(
                    {
                        "asset": str(asset),
                        "timeframe": str(timeframe),
                        "market": str(market_type),
                        "did": _bar_direction_text(latest, previous),
                        "doing": _range_text(latest),
                        "next_monitor": _next_monitor_briefing(state, ladder, latest),
                        "key_levels": _key_levels_text(ladder),
                        "risk_context": _risk_context_text(
                            ohlcv_coverage,
                            book_coverage,
                            dispersion_pct,
                            depth_imbalance,
                            state,
                        ),
                        "operator_mode": operator_mode,
                    }
                )
    return items


def _operational_briefing_cards(artifact_root: Path, quality: dict[str, Any]) -> str:
    items = _operational_briefing_items(artifact_root, quality)
    if not items:
        return (
            '<div class="briefing-card-grid">'
            '<div class="briefing-card">No operational briefing could be derived from the artifact root.</div>'
            '</div>'
        )

    cards: list[str] = []
    for item in items:
        operator_mode = item["operator_mode"]
        operator_class = "ok" if operator_mode == "OBSERVE" else "warn"
        cards.append(
            '<article class="briefing-card">'
            f'<h3>{_html_text(item["asset"])} / {_html_text(item["timeframe"])} / {_html_text(item["market"])}</h3>'
            '<div class="briefing-meta">'
            '<span class="badge neutral">Monitor-only context</span> '
            f'<span class="badge {operator_class}">{_html_text(operator_mode)}</span>'
            '</div>'
            '<div class="briefing-block"><div class="briefing-label">DID</div>'
            f'<div class="briefing-value">{_html_text(item["did"])}</div></div>'
            '<div class="briefing-block"><div class="briefing-label">DOING</div>'
            f'<div class="briefing-value">{_html_text(item["doing"])}</div></div>'
            '<div class="briefing-block"><div class="briefing-label">NEXT MONITOR</div>'
            f'<div class="briefing-value">{_html_text(item["next_monitor"])}</div></div>'
            '<div class="briefing-block"><div class="briefing-label">KEY LEVELS</div>'
            f'<div class="briefing-value">{_html_text(item["key_levels"])}</div></div>'
            '<div class="briefing-block"><div class="briefing-label">RISK CONTEXT</div>'
            f'<div class="briefing-value">{_html_text(item["risk_context"])}</div></div>'
            '</article>'
        )
    return '<div class="briefing-card-grid">' + "\n".join(cards) + '</div>'


def _operational_briefing_rows(artifact_root: Path, quality: dict[str, Any]) -> str:
    rows: list[str] = []
    for asset, asset_root in _asset_report_roots(artifact_root, quality):
        ohlcv_by_tf = _as_mapping(_read_json(asset_root / "composite_ohlcv.json"))
        ladder_by_tf = _as_mapping(_read_json(asset_root / "composite_orderbook_ladder.json"))
        for timeframe, ohlcv_context_raw in sorted(ohlcv_by_tf.items()):
            ohlcv_context = _as_mapping(ohlcv_context_raw)
            coverage_by_market_type = _as_mapping(ohlcv_context.get("coverage_by_market_type"))
            status_by_market_type = _as_mapping(ohlcv_context.get("status_by_market_type"))
            latest_by_market_type = _as_mapping(ohlcv_context.get("latest_by_market_type"))
            ladder_for_timeframe = _as_mapping(ladder_by_tf.get(timeframe))
            market_types = sorted(set(coverage_by_market_type) | set(latest_by_market_type) | set(ladder_for_timeframe))
            if not market_types:
                market_types = ["artifact"]

            tf_quality = _quality_lookup(quality, asset, timeframe)
            tf_grade = tf_quality.get("quality_grade") or "n/a"

            for market_type in market_types:
                latest = _latest_bar(ohlcv_context, market_type)
                previous = _previous_bar(ohlcv_context, market_type)
                ladder = _as_mapping(ladder_for_timeframe.get(market_type))
                ohlcv_coverage = coverage_by_market_type.get(market_type)
                ohlcv_status = status_by_market_type.get(market_type)
                book_coverage = ladder.get("coverage")
                book_status = ladder.get("status")
                dispersion_pct = latest.get("price_dispersion_pct")
                depth_imbalance = ladder.get("depth_imbalance")
                state, operator_mode, _context_next = _operational_state(
                    tf_grade,
                    ohlcv_coverage,
                    ohlcv_status,
                    book_coverage,
                    book_status,
                    dispersion_pct,
                    depth_imbalance,
                )
                rows.append(
                    "<tr>"
                    f"<td>{_html_text(asset)}</td>"
                    f"<td>{_html_text(timeframe)}</td>"
                    f"<td>{_html_text(market_type)}</td>"
                    f"<td>{_html_text(_bar_direction_text(latest, previous))}</td>"
                    f"<td>{_html_text(_range_text(latest))}</td>"
                    f"<td>{_html_text(_next_monitor_briefing(state, ladder, latest))}</td>"
                    f"<td>{_html_text(_key_levels_text(ladder))}</td>"
                    f"<td>{_html_text(_risk_context_text(ohlcv_coverage, book_coverage, dispersion_pct, depth_imbalance, state))}</td>"
                    f"<td>{_html_text(operator_mode)}</td>"
                    "</tr>"
                )
    if not rows:
        return "<tr><td colspan=\"9\">No operational briefing could be derived from the artifact root.</td></tr>"
    return "\n".join(rows)


def _operational_briefing_summary(quality: dict[str, Any]) -> str:
    status = str(quality.get("status", "UNKNOWN")).upper()
    grade = str(quality.get("quality_grade", "n/a")).upper()
    assets_checked = quality.get("assets_checked", "n/a")
    if status == "OK" and grade in {"A", "B"}:
        briefing_state = "READY FOR REVIEW"
    elif status == "WARN":
        briefing_state = "REVIEW WITH CAVEATS"
    else:
        briefing_state = "VERIFY FIRST"
    return (
        "<div class=\"grid\">"
        f"<div class=\"metric\">Briefing state<strong>{_html_text(briefing_state)}</strong></div>"
        "<div class=\"metric\">Briefing mode<strong>Monitor-only</strong></div>"
        f"<div class=\"metric\">Assets summarized<strong>{_html_text(assets_checked)}</strong></div>"
        "<div class=\"metric\">Decision boundary<strong>No execution guidance</strong></div>"
        "</div>"
    )


def _operational_context_rows(artifact_root: Path, quality: dict[str, Any]) -> str:
    rows: list[str] = []
    for asset, asset_root in _asset_report_roots(artifact_root, quality):
        ohlcv_by_tf = _as_mapping(_read_json(asset_root / "composite_ohlcv.json"))
        ladder_by_tf = _as_mapping(_read_json(asset_root / "composite_orderbook_ladder.json"))
        for timeframe, ohlcv_context_raw in sorted(ohlcv_by_tf.items()):
            ohlcv_context = _as_mapping(ohlcv_context_raw)
            coverage_by_market_type = _as_mapping(ohlcv_context.get("coverage_by_market_type"))
            status_by_market_type = _as_mapping(ohlcv_context.get("status_by_market_type"))
            latest_by_market_type = _as_mapping(ohlcv_context.get("latest_by_market_type"))
            ladder_for_timeframe = _as_mapping(ladder_by_tf.get(timeframe))
            market_types = sorted(set(coverage_by_market_type) | set(ladder_for_timeframe))
            if not market_types:
                market_types = ["artifact"]

            tf_quality = _quality_lookup(quality, asset, timeframe)
            tf_grade = tf_quality.get("quality_grade") or "n/a"
            tf_score = tf_quality.get("quality_score") or "n/a"

            for market_type in market_types:
                latest = _as_mapping(latest_by_market_type.get(market_type))
                ladder = _as_mapping(ladder_for_timeframe.get(market_type))
                ohlcv_coverage = coverage_by_market_type.get(market_type)
                ohlcv_status = status_by_market_type.get(market_type)
                book_coverage = ladder.get("coverage")
                book_status = ladder.get("status")
                dispersion_pct = latest.get("price_dispersion_pct")
                depth_imbalance = ladder.get("depth_imbalance")
                state, operator_mode, next_monitor = _operational_state(
                    tf_grade,
                    ohlcv_coverage,
                    ohlcv_status,
                    book_coverage,
                    book_status,
                    dispersion_pct,
                    depth_imbalance,
                )
                rows.append(
                    "<tr>"
                    f"<td>{_html_text(asset)}</td>"
                    f"<td>{_html_text(timeframe)}</td>"
                    f"<td>{_html_text(market_type)}</td>"
                    f"<td><span class=\"badge {_status_class('OK' if state == 'OBSERVATION READY' else 'WARN')}\">{_html_text(state)}</span></td>"
                    f"<td>{_html_text(operator_mode)}</td>"
                    f"<td>{_html_text(next_monitor)}</td>"
                    f"<td>OHLCV {_html_text(_ratio_pct(ohlcv_coverage))}<br>Book {_html_text(_ratio_pct(book_coverage))}</td>"
                    f"<td>{_html_text(_plain_number(dispersion_pct, 4))}%</td>"
                    f"<td>{_html_text(_depth_balance_text(depth_imbalance))}</td>"
                    f"<td>{_html_text(tf_score)} / {_html_text(tf_grade)}</td>"
                    "</tr>"
                )
    if not rows:
        return "<tr><td colspan=\"10\">No operational context could be derived from the artifact root.</td></tr>"
    return "\n".join(rows)


def _operational_context_summary(quality: dict[str, Any]) -> str:
    status = str(quality.get("status", "UNKNOWN")).upper()
    grade = str(quality.get("quality_grade", "n/a")).upper()
    assets_checked = quality.get("assets_checked", "n/a")
    if status == "OK" and grade in {"A", "B"}:
        mission = "Artifact set is suitable for monitor-only review."
    elif status == "WARN":
        mission = "Artifact set is usable with data-quality caveats."
    else:
        mission = "Artifact set needs validation before operational review."
    return (
        "<div class=\"grid\">"
        f"<div class=\"metric\">Mission<strong>{_html_text(mission)}</strong></div>"
        f"<div class=\"metric\">Operator mode<strong>{_html_text('OBSERVE' if status == 'OK' else 'VERIFY DATA')}</strong></div>"
        f"<div class=\"metric\">Assets in scope<strong>{_html_text(assets_checked)}</strong></div>"
        f"<div class=\"metric\">Context boundary<strong>Monitor-only public data</strong></div>"
        "</div>"
    )


def _artifact_link_items(root: Path, report_file: Path) -> str:
    links = _collect_artifact_links(root, report_file)
    if not links:
        return "<li>No JSON artifacts found.</li>"
    return "\n".join(
        f"<li><a href=\"{_html_text(item['href'])}\">{_html_text(item['path'])}</a></li>" for item in links
    )


def _render_html(artifact_root: Path, report_file: Path, quality: dict[str, Any]) -> str:
    warnings = _as_list(quality.get("warnings"))
    errors = _as_list(quality.get("errors"))
    validation = _as_mapping(quality.get("validation"))
    status = quality.get("status", "unknown")
    grade = quality.get("quality_grade", "F")
    score = quality.get("quality_score", 0.0)

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Crypto Composite Artifact Report</title>
  <style>
    :root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; padding: 32px; background: Canvas; color: CanvasText; }}
    main {{ max-width: 1180px; margin: 0 auto; }}
    h1, h2 {{ letter-spacing: -0.02em; }}
    .card {{ border: 1px solid color-mix(in srgb, CanvasText 18%, transparent); border-radius: 14px; padding: 20px; margin: 18px 0; background: color-mix(in srgb, Canvas 94%, CanvasText 6%); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid color-mix(in srgb, CanvasText 14%, transparent); border-radius: 12px; padding: 14px; }}
    .metric strong {{ display: block; font-size: 1.6rem; margin-top: 6px; }}
    .metric strong {{ overflow-wrap: anywhere; }}
    .context-note {{ margin-top: 8px; color: color-mix(in srgb, CanvasText 72%, transparent); }}
    .briefing-card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; margin-top: 14px; }}
    .briefing-card {{ border: 1px solid color-mix(in srgb, CanvasText 14%, transparent); border-radius: 14px; padding: 16px; background: color-mix(in srgb, Canvas 90%, CanvasText 10%); }}
    .briefing-card h3 {{ margin: 0 0 8px; letter-spacing: -0.01em; }}
    .briefing-meta {{ color: color-mix(in srgb, CanvasText 72%, transparent); font-size: 0.92rem; margin-bottom: 12px; }}
    .briefing-block {{ margin-top: 12px; }}
    .briefing-label {{ font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 800; color: color-mix(in srgb, CanvasText 66%, transparent); }}
    .briefing-value {{ margin-top: 3px; overflow-wrap: anywhere; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
    th, td {{ border-bottom: 1px solid color-mix(in srgb, CanvasText 16%, transparent); padding: 10px; text-align: left; vertical-align: top; }}
    th {{ font-size: 0.86rem; text-transform: uppercase; letter-spacing: 0.04em; }}
    code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    pre {{ overflow-x: auto; border-radius: 12px; padding: 14px; background: color-mix(in srgb, CanvasText 9%, transparent); }}
    a {{ color: LinkText; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 4px 9px; font-weight: 700; }}
    .ok {{ background: color-mix(in srgb, green 24%, transparent); }}
    .warn {{ background: color-mix(in srgb, orange 28%, transparent); }}
    .error {{ background: color-mix(in srgb, red 25%, transparent); }}
    .neutral {{ background: color-mix(in srgb, CanvasText 12%, transparent); }}
    .boundary {{ font-weight: 700; }}
  </style>
</head>
<body>
<main>
  <h1>Crypto Composite Artifact Report</h1>
  <p class=\"boundary\">Static data-quality report only. No trade call, execution instruction, position sizing, prediction, or financial advice.</p>

  <section class=\"card\">
    <h2>Summary</h2>
    <div class=\"grid\">
      <div class=\"metric\">Status<strong><span class=\"badge {_status_class(status)}\">{_html_text(status)}</span></strong></div>
      <div class=\"metric\">Quality score<strong>{_html_text(score)}</strong></div>
      <div class=\"metric\">Quality grade<strong><span class=\"badge {_grade_class(grade)}\">{_html_text(grade)}</span></strong></div>
      <div class=\"metric\">Assets checked<strong>{_html_text(quality.get('assets_checked'))}</strong></div>
      <div class=\"metric\">Mode<strong>{_html_text(quality.get('mode'))}</strong></div>
      <div class=\"metric\">Artifact root<strong>{_html_text(artifact_root)}</strong></div>
    </div>
  </section>


  <section class=\"card\">
    <h2>Operational briefing</h2>
    <p class=\"context-note\">LFX-style DID / DOING / NEXT / KEY LEVELS summary derived from composite OHLCV and public ladder artifacts. Monitor-only context; no execution guidance.</p>
    {_operational_briefing_summary(quality)}
    {_operational_briefing_cards(artifact_root, quality)}
    <table>
      <thead><tr><th>Asset</th><th>Timeframe</th><th>Market</th><th>DID</th><th>DOING</th><th>NEXT MONITOR</th><th>KEY LEVELS</th><th>RISK CONTEXT</th><th>Operator mode</th></tr></thead>
      <tbody>{_operational_briefing_rows(artifact_root, quality)}</tbody>
    </table>
  </section>

  <section class=\"card\">
    <h2>Operational context</h2>
    <p class=\"context-note\">LFX-style monitor-only context derived from composite coverage, venue dispersion, and public orderbook depth. This is not a trading signal.</p>
    {_operational_context_summary(quality)}
    <table>
      <thead><tr><th>Asset</th><th>Timeframe</th><th>Market</th><th>Mission</th><th>Operator mode</th><th>Next monitor</th><th>Coverage</th><th>Price dispersion</th><th>Depth balance</th><th>Quality</th></tr></thead>
      <tbody>{_operational_context_rows(artifact_root, quality)}</tbody>
    </table>
  </section>

  <section class=\"card\">
    <h2>Assets</h2>
    <table>
      <thead><tr><th>Asset</th><th>Score</th><th>Grade</th><th>Timeframes</th><th>Warnings</th></tr></thead>
      <tbody>{_asset_rows(quality)}</tbody>
    </table>
  </section>

  <section class=\"card\">
    <h2>Timeframe components</h2>
    <table>
      <thead><tr><th>Asset</th><th>Timeframe</th><th>Score</th><th>Grade</th><th>Venue coverage</th><th>OHLCV coverage</th><th>OHLCV status</th><th>Price dispersion</th><th>Book coverage</th><th>Book status</th></tr></thead>
      <tbody>{_timeframe_rows(quality)}</tbody>
    </table>
  </section>

  <section class=\"card\">
    <h2>Warnings and errors</h2>
    <h3>Warnings</h3>
    <pre>{_json_block(warnings)}</pre>
    <h3>Errors</h3>
    <pre>{_json_block(errors)}</pre>
  </section>

  <section class=\"card\">
    <h2>Validation summary</h2>
    <pre>{_json_block(validation)}</pre>
  </section>

  <section class=\"card\">
    <h2>Artifact files</h2>
    <ul>{_artifact_link_items(artifact_root, report_file)}</ul>
  </section>
</main>
</body>
</html>
"""
    return html


def assert_no_forbidden_report_terms(html: str) -> None:
    upper = html.upper()
    matched = [
        term
        for term in _FORBIDDEN_REPORT_TERMS
        if re.search(rf"(?<![A-Z0-9_]){re.escape(term)}(?![A-Z0-9_])", upper)
    ]
    if matched:
        raise ValueError(f"FORBIDDEN_REPORT_TERM: {', '.join(matched)}")


def write_static_report(artifact_root: str | Path, out_file: str | Path) -> dict[str, Any]:
    root = Path(artifact_root)
    report_file = Path(out_file)
    quality = score_artifact_root(root)
    html = _render_html(root, report_file, quality)
    assert_no_forbidden_report_terms(html)

    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(html, encoding="utf-8")

    return {
        "status": quality.get("status", "ERROR"),
        "artifact_root": str(root),
        "report_path": str(report_file),
        "quality_score": quality.get("quality_score"),
        "quality_grade": quality.get("quality_grade"),
        "assets_checked": quality.get("assets_checked", 0),
        "errors": quality.get("errors", []),
        "warnings": quality.get("warnings", []),
        "boundaries": [NO_SIGNAL_BOUNDARY],
    }
