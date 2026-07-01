from __future__ import annotations

import json
import os
import re
from html import escape
from pathlib import Path
from typing import Any

from crypto_composite.artifact_quality import score_artifact_root
from crypto_composite.artifact_validator import validate_artifact_root
from crypto_composite.dashboard_analytics import build_dashboard_snapshot
from crypto_composite.lfx_alignment import build_lfx_alignment


NO_SIGNAL_BOUNDARY = (
    "Research dataset report only; no trading signal, ranking, prediction, execution instruction, "
    "position sizing, profitability claim, or financial advice."
)
_FORBIDDEN_RESEARCH_TERMS = ("BUY", "SELL", "ENTRY", "TAKE PROFIT", "STOP LOSS")


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _rounded(value: Any, digits: int = 6) -> float | None:
    number = _number(value)
    return round(number, digits) if number is not None else None


def _html_text(value: Any) -> str:
    if value is None:
        return "unavailable"
    return escape(str(value), quote=True)


def _json_block(value: Any) -> str:
    return escape(json.dumps(value, indent=2, sort_keys=True), quote=False)


def _rel_link(target: Path, base_file: Path) -> str:
    try:
        return Path(os.path.relpath(target.resolve(), start=base_file.resolve().parent)).as_posix()
    except ValueError:
        return target.resolve().as_uri()


def _status_from(parts: list[Any]) -> str:
    statuses = {str(part).upper() for part in parts if part is not None}
    if "ERROR" in statuses:
        return "ERROR"
    if "WARN" in statuses:
        return "WARN"
    if statuses == {"OK"}:
        return "OK"
    return "WARN" if statuses else "ERROR"


def _artifact_inventory(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    artifacts: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.json")):
        if not path.is_file():
            continue
        try:
            rel_path = path.relative_to(root).as_posix()
        except ValueError:
            rel_path = str(path)
        artifacts.append({"path": rel_path, "bytes": path.stat().st_size})
    return artifacts


def _unique_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if isinstance(value, str) and value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _compact_zone(zone: Any) -> dict[str, Any] | None:
    item = _as_mapping(zone)
    if not item:
        return None
    return {
        "kind": item.get("kind"),
        "label": item.get("label"),
        "side": item.get("side"),
        "price_low": _rounded(item.get("price_low")),
        "price_high": _rounded(item.get("price_high")),
        "reference_relation": item.get("reference_relation"),
        "distance_to_reference_pct": _rounded(item.get("distance_to_reference_pct")),
        "depth_quote": _rounded(item.get("depth_quote"), 2),
        "venue_count": item.get("venue_count"),
        "hhi": _rounded(item.get("hhi"), 4),
        "persistence_proxy": _rounded(item.get("persistence_proxy"), 4),
        "vacuum_score": _rounded(item.get("vacuum_score"), 4),
        "evidence_grade": item.get("evidence_grade"),
        "majority_venue_share": _rounded(item.get("majority_venue_share"), 4),
    }


def _zone_mix(market: dict[str, Any]) -> dict[str, int | None]:
    readout = _as_mapping(market.get("zone_readout"))
    mix = _as_mapping(readout.get("evidence_mix"))
    zones = [_as_mapping(zone) for zone in _as_list(market.get("observed_zones"))]
    if mix:
        return {
            "total_zones": mix.get("total_zones"),
            "corroborated": mix.get("corroborated"),
            "concentrated": mix.get("concentrated"),
            "limited": mix.get("limited"),
        }
    return {
        "total_zones": len(zones),
        "corroborated": sum(1 for zone in zones if zone.get("evidence_grade") == "CORROBORATED"),
        "concentrated": sum(1 for zone in zones if zone.get("evidence_grade") == "CONCENTRATED"),
        "limited": sum(1 for zone in zones if zone.get("evidence_grade") == "LIMITED"),
    }


def _market_microstructure_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in _as_list(snapshot.get("assets")):
        asset_obj = _as_mapping(asset)
        asset_name = asset_obj.get("asset")
        for timeframe in _as_list(asset_obj.get("timeframes")):
            timeframe_obj = _as_mapping(timeframe)
            timeframe_name = timeframe_obj.get("timeframe")
            for market in _as_list(timeframe_obj.get("markets")):
                market_obj = _as_mapping(market)
                latest = _as_mapping(market_obj.get("latest_bar"))
                orderbook = _as_mapping(market_obj.get("orderbook"))
                rows.append(
                    {
                        "asset": asset_name,
                        "timeframe": timeframe_name,
                        "market_type": market_obj.get("market_type"),
                        "generated_at_ms": market_obj.get("generated_at_ms"),
                        "ohlcv_status": market_obj.get("ohlcv_status"),
                        "bar_count": len(_as_list(market_obj.get("bars"))),
                        "latest_timestamp_ms": latest.get("timestamp_ms"),
                        "latest_close": _rounded(latest.get("close")),
                        "latest_venue_count": latest.get("venue_count"),
                        "latest_coverage": _rounded(latest.get("coverage"), 4),
                        "price_dispersion_pct": _rounded(latest.get("price_dispersion_pct"), 6),
                        "orderbook_status": orderbook.get("status"),
                        "orderbook_coverage": _rounded(orderbook.get("coverage"), 4),
                        "orderbook_venue_count": orderbook.get("venue_count"),
                        "reference_price": _rounded(orderbook.get("reference_price")),
                        "bucket_size": _rounded(orderbook.get("bucket_size")),
                        "bid_depth_total": _rounded(orderbook.get("bid_depth_total"), 2),
                        "ask_depth_total": _rounded(orderbook.get("ask_depth_total"), 2),
                        "depth_imbalance": _rounded(orderbook.get("depth_imbalance"), 6),
                        "top_bid_wall": _compact_zone(orderbook.get("top_bid_wall")),
                        "top_ask_wall": _compact_zone(orderbook.get("top_ask_wall")),
                    }
                )
    return rows


def _observed_zone_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in _as_list(snapshot.get("assets")):
        asset_obj = _as_mapping(asset)
        asset_name = asset_obj.get("asset")
        for timeframe in _as_list(asset_obj.get("timeframes")):
            timeframe_obj = _as_mapping(timeframe)
            timeframe_name = timeframe_obj.get("timeframe")
            for market in _as_list(timeframe_obj.get("markets")):
                market_obj = _as_mapping(market)
                readout = _as_mapping(market_obj.get("zone_readout"))
                monitoring = _as_mapping(market_obj.get("monitoring_brief"))
                now = _as_mapping(monitoring.get("now"))
                zones = [
                    compact
                    for zone in _as_list(market_obj.get("observed_zones"))
                    if (compact := _compact_zone(zone)) is not None
                ]
                rows.append(
                    {
                        "asset": asset_name,
                        "timeframe": timeframe_name,
                        "market_type": market_obj.get("market_type"),
                        "evidence_mix": _zone_mix(market_obj),
                        "nearest_bid_concentration": _compact_zone(now.get("nearest_bid_concentration")),
                        "nearest_ask_concentration": _compact_zone(now.get("nearest_ask_concentration")),
                        "observed_zones": zones,
                        "readout_title": readout.get("title"),
                        "readout_detail": readout.get("detail"),
                        "next_evidence_check": readout.get("next_check"),
                        "limitation": readout.get("limitation"),
                    }
                )
    return rows


def _mission_control_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in _as_list(snapshot.get("assets")):
        asset_obj = _as_mapping(asset)
        asset_name = asset_obj.get("asset")
        for timeframe in _as_list(asset_obj.get("timeframes")):
            timeframe_obj = _as_mapping(timeframe)
            timeframe_name = timeframe_obj.get("timeframe")
            for market in _as_list(timeframe_obj.get("markets")):
                market_obj = _as_mapping(market)
                mission_control = _as_mapping(market_obj.get("lfx_mission_control"))
                for row in _as_list(mission_control.get("rows")):
                    item = _as_mapping(row)
                    rows.append(
                        {
                            "asset": asset_name,
                            "timeframe": timeframe_name,
                            "market_type": market_obj.get("market_type"),
                            "panel": item.get("panel"),
                            "title": item.get("title"),
                            "detail": item.get("detail"),
                            "artifact_basis": _as_list(item.get("artifact_basis")),
                            "boundary": mission_control.get("boundary"),
                        }
                    )
    return rows


def _dataset_scope(snapshot: dict[str, Any], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    assets = [_as_mapping(asset) for asset in _as_list(snapshot.get("assets"))]
    asset_names = _unique_strings([asset.get("asset") for asset in assets])
    timeframe_values: list[Any] = []
    market_values: list[Any] = []
    for asset in assets:
        for timeframe in _as_list(asset.get("timeframes")):
            timeframe_obj = _as_mapping(timeframe)
            timeframe_values.append(timeframe_obj.get("timeframe"))
            for market in _as_list(timeframe_obj.get("markets")):
                market_values.append(_as_mapping(market).get("market_type"))
    profile = _as_mapping(snapshot.get("profile"))
    return {
        "assets": asset_names,
        "asset_count": len(asset_names),
        "timeframes": _unique_strings(timeframe_values),
        "market_types": _unique_strings(market_values),
        "primary_timeframe": profile.get("primary_timeframe"),
        "profile_timeframes": _as_list(profile.get("timeframes")),
        "refresh_seconds": profile.get("refresh_seconds"),
        "json_artifact_count": len(artifacts),
    }


def build_research_summary(artifact_root: str | Path) -> dict[str, Any]:
    """Build a static, non-predictive research summary from generated artifacts."""
    root = Path(artifact_root)
    validation = validate_artifact_root(root)
    quality = score_artifact_root(root)
    artifacts = _artifact_inventory(root)
    snapshot_errors: list[dict[str, str]] = []
    try:
        snapshot = build_dashboard_snapshot(root)
    except Exception as exc:  # pragma: no cover - defensive report path
        snapshot = {"mode": None, "profile": {}, "assets": [], "boundaries": []}
        snapshot_errors.append({"code": "DASHBOARD_SNAPSHOT_ERROR", "message": str(exc)})

    microstructure_rows = _market_microstructure_rows(snapshot)
    zone_rows = _observed_zone_rows(snapshot)
    mission_rows = _mission_control_rows(snapshot)
    errors = list(_as_list(validation.get("errors"))) + list(_as_list(quality.get("errors"))) + snapshot_errors
    warnings = list(_as_list(validation.get("warnings"))) + list(_as_list(quality.get("warnings")))
    status = _status_from(
        [
            validation.get("status"),
            quality.get("status"),
            "ERROR" if snapshot_errors else "OK",
        ]
    )
    dataset = _dataset_scope(snapshot, artifacts)

    return {
        "status": status,
        "artifact_root": str(root),
        "mode": validation.get("mode"),
        "dataset": dataset,
        "quality": {
            "status": quality.get("status"),
            "quality_score": quality.get("quality_score"),
            "quality_grade": quality.get("quality_grade"),
            "assets_checked": quality.get("assets_checked"),
        },
        "validation": validation,
        "profile": _as_mapping(snapshot.get("profile")),
        "lfx_alignment": _as_mapping(snapshot.get("lfx_alignment")) or build_lfx_alignment(_as_mapping(snapshot.get("profile"))),
        "lfx_mission_control": mission_rows,
        "market_microstructure_metrics": microstructure_rows,
        "observed_zone_evidence": zone_rows,
        "artifacts": artifacts,
        "research_questions_supported": [
            "Which generated assets, timeframes, market types, and JSON artifacts are available for inspection?",
            "How complete are composite OHLCV and public orderbook artifacts across requested venues?",
            "What are the latest public microstructure metrics: venue coverage, price dispersion, depth totals, imbalance, and concentration?",
            "Which observed public-depth ranges have corroborated, concentrated, or limited evidence in the generated snapshot?",
        ],
        "limitations": [
            "Static report over generated artifacts; refresh artifacts before comparing a newer market state.",
            "Observed zones are public orderbook bucket diagnostics, not support/resistance, hidden-liquidity proof, or future-reaction evidence.",
            NO_SIGNAL_BOUNDARY,
        ],
        "errors": errors,
        "warnings": warnings,
        "boundaries": [NO_SIGNAL_BOUNDARY],
    }


def _status_class(status: Any) -> str:
    status_text = str(status).upper()
    if status_text == "OK":
        return "ok"
    if status_text == "ERROR":
        return "error"
    return "warn"


def _metric(value: Any, digits: int | None = None) -> str:
    number = _number(value)
    if number is None:
        return _html_text(value)
    if digits is None:
        return _html_text(round(number, 6))
    return _html_text(round(number, digits))


def _zone_text(zone: dict[str, Any] | None) -> str:
    if zone is None:
        return "unavailable"
    low = _metric(zone.get("price_low"))
    high = _metric(zone.get("price_high"))
    distance = _metric(zone.get("distance_to_reference_pct"), 3)
    relation = zone.get("reference_relation")
    grade = zone.get("evidence_grade")
    depth = _metric(zone.get("depth_quote"), 0)
    venue_count = zone.get("venue_count")
    return (
        f"{low} - {high}; relation {_html_text(relation)}; distance {distance}%; "
        f"depth {depth}; venues {_html_text(venue_count)}; evidence {_html_text(grade)}"
    )


def _summary_bullets(summary: dict[str, Any]) -> str:
    dataset = _as_mapping(summary.get("dataset"))
    quality = _as_mapping(summary.get("quality"))
    asset_count = dataset.get("asset_count")
    timeframes = ", ".join(str(item) for item in _as_list(dataset.get("timeframes"))) or "unavailable"
    market_types = ", ".join(str(item) for item in _as_list(dataset.get("market_types"))) or "unavailable"
    artifact_count = dataset.get("json_artifact_count")
    rows = len(_as_list(summary.get("market_microstructure_metrics")))
    zone_rows = len(_as_list(summary.get("observed_zone_evidence")))
    mission_rows = len(_as_list(summary.get("lfx_mission_control")))
    bullets = [
        (
            "<strong>Dataset scope.</strong> "
            f"{_html_text(asset_count)} assets, timeframes {escape(timeframes)}, market types {escape(market_types)}, "
            f"and {_html_text(artifact_count)} JSON artifacts are available in this artifact root."
        ),
        (
            "<strong>Research utility.</strong> "
            f"The report exposes {_html_text(rows)} market microstructure rows, {_html_text(zone_rows)} observed-zone "
            f"evidence rows, and {_html_text(mission_rows)} mission-control rows for audit, notebook intake, and public demo sharing."
        ),
        (
            "<strong>Quality gate.</strong> "
            f"Current quality status is {_html_text(quality.get('status'))}, grade {_html_text(quality.get('quality_grade'))}, "
            f"score {_html_text(quality.get('quality_score'))}."
        ),
        (
            "<strong>Boundary.</strong> "
            "No trading signal, ranking, prediction, execution instruction, profitability claim, or financial advice is produced."
        ),
    ]
    return "".join(f"<li>{bullet}</li>" for bullet in bullets)


def _microstructure_table(rows: list[Any]) -> str:
    if not rows:
        return '<tr><td colspan="9">No market microstructure rows were found.</td></tr>'
    html_rows: list[str] = []
    for row in rows:
        item = _as_mapping(row)
        depth = f"{_metric(item.get('bid_depth_total'), 0)} / {_metric(item.get('ask_depth_total'), 0)}"
        html_rows.append(
            "<tr>"
            f"<td>{_html_text(item.get('asset'))}</td>"
            f"<td>{_html_text(item.get('timeframe'))}</td>"
            f"<td>{_html_text(item.get('market_type'))}</td>"
            f"<td>{_html_text(item.get('ohlcv_status'))}</td>"
            f"<td>{_metric(item.get('latest_close'))}</td>"
            f"<td>{_metric(item.get('price_dispersion_pct'), 4)}%</td>"
            f"<td>{_html_text(item.get('orderbook_status'))}</td>"
            f"<td>{depth}</td>"
            f"<td>{_metric(item.get('depth_imbalance'), 4)}</td>"
            "</tr>"
        )
    return "".join(html_rows)


def _zone_table(rows: list[Any]) -> str:
    if not rows:
        return '<tr><td colspan="8">No observed-zone rows were found.</td></tr>'
    html_rows: list[str] = []
    for row in rows:
        item = _as_mapping(row)
        mix = _as_mapping(item.get("evidence_mix"))
        mix_text = (
            f"total {_html_text(mix.get('total_zones'))}; "
            f"corroborated {_html_text(mix.get('corroborated'))}; "
            f"concentrated {_html_text(mix.get('concentrated'))}; "
            f"limited {_html_text(mix.get('limited'))}"
        )
        html_rows.append(
            "<tr>"
            f"<td>{_html_text(item.get('asset'))}</td>"
            f"<td>{_html_text(item.get('timeframe'))}</td>"
            f"<td>{_html_text(item.get('market_type'))}</td>"
            f"<td>{mix_text}</td>"
            f"<td>{_zone_text(_compact_zone(item.get('nearest_bid_concentration')))}</td>"
            f"<td>{_zone_text(_compact_zone(item.get('nearest_ask_concentration')))}</td>"
            f"<td>{_html_text(item.get('next_evidence_check'))}</td>"
            f"<td>{_html_text(item.get('limitation'))}</td>"
            "</tr>"
        )
    return "".join(html_rows)


def _artifact_table(rows: list[Any], report_file: Path, artifact_root: Path) -> str:
    if not rows:
        return '<tr><td colspan="3">No JSON artifacts were found.</td></tr>'
    html_rows: list[str] = []
    for row in rows:
        item = _as_mapping(row)
        rel_path = item.get("path")
        target = artifact_root / str(rel_path) if isinstance(rel_path, str) else artifact_root
        href = _rel_link(target, report_file)
        html_rows.append(
            "<tr>"
            f"<td><a href=\"{_html_text(href)}\">{_html_text(rel_path)}</a></td>"
            f"<td>{_html_text(item.get('bytes'))}</td>"
            f"<td>JSON artifact</td>"
            "</tr>"
        )
    return "".join(html_rows)


def _lfx_contract_table(rows: list[Any]) -> str:
    if not rows:
        return '<tr><td colspan="4">No LFX alignment contract rows were found.</td></tr>'
    html_rows: list[str] = []
    for row in rows:
        item = _as_mapping(row)
        basis = ", ".join(str(value) for value in _as_list(item.get("artifact_basis")))
        fields = ", ".join(str(value) for value in _as_list(item.get("output_fields")))
        html_rows.append(
            "<tr>"
            f"<td>{_html_text(item.get('panel'))}</td>"
            f"<td>{_html_text(item.get('question'))}</td>"
            f"<td>{_html_text(basis)}</td>"
            f"<td>{_html_text(fields)}</td>"
            "</tr>"
        )
    return "".join(html_rows)


def _mission_control_table(rows: list[Any]) -> str:
    if not rows:
        return '<tr><td colspan="7">No LFX mission-control rows were found.</td></tr>'
    html_rows: list[str] = []
    for row in rows:
        item = _as_mapping(row)
        basis = ", ".join(str(value) for value in _as_list(item.get("artifact_basis")))
        html_rows.append(
            "<tr>"
            f"<td>{_html_text(item.get('asset'))}</td>"
            f"<td>{_html_text(item.get('timeframe'))}</td>"
            f"<td>{_html_text(item.get('market_type'))}</td>"
            f"<td>{_html_text(item.get('panel'))}</td>"
            f"<td>{_html_text(item.get('title'))}</td>"
            f"<td>{_html_text(item.get('detail'))}</td>"
            f"<td>{_html_text(basis)}</td>"
            "</tr>"
        )
    return "".join(html_rows)


def _render_html(summary: dict[str, Any], report_file: Path, summary_file: Path) -> str:
    dataset = _as_mapping(summary.get("dataset"))
    lfx_alignment = _as_mapping(summary.get("lfx_alignment"))
    artifacts = _as_list(summary.get("artifacts"))
    mission_rows = _as_list(summary.get("lfx_mission_control"))
    microstructure_rows = _as_list(summary.get("market_microstructure_metrics"))
    zone_rows = _as_list(summary.get("observed_zone_evidence"))
    artifact_root = Path(str(summary.get("artifact_root")))
    summary_href = _rel_link(summary_file, report_file)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Crypto Composite Research Dataset Report</title>
  <style>
    :root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; padding: 32px; background: Canvas; color: CanvasText; }}
    main {{ max-width: 1180px; margin: 0 auto; }}
    h1, h2 {{ letter-spacing: -0.02em; }}
    .card {{ border: 1px solid color-mix(in srgb, CanvasText 18%, transparent); border-radius: 14px; padding: 20px; margin: 18px 0; background: color-mix(in srgb, Canvas 94%, CanvasText 6%); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid color-mix(in srgb, CanvasText 14%, transparent); border-radius: 12px; padding: 14px; }}
    .metric strong {{ display: block; font-size: 1.45rem; margin-top: 6px; overflow-wrap: anywhere; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 4px 9px; font-weight: 700; }}
    .ok {{ background: color-mix(in srgb, green 24%, transparent); }}
    .warn {{ background: color-mix(in srgb, orange 28%, transparent); }}
    .error {{ background: color-mix(in srgb, red 25%, transparent); }}
    .boundary {{ font-weight: 700; }}
    .note {{ color: color-mix(in srgb, CanvasText 72%, transparent); }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
    th, td {{ border-bottom: 1px solid color-mix(in srgb, CanvasText 16%, transparent); padding: 10px; text-align: left; vertical-align: top; }}
    th {{ font-size: 0.84rem; text-transform: uppercase; letter-spacing: 0.04em; }}
    pre {{ overflow-x: auto; border-radius: 12px; padding: 14px; background: color-mix(in srgb, CanvasText 9%, transparent); }}
    a {{ color: LinkText; }}
  </style>
</head>
<body>
<main>
  <h1>Crypto Composite Research Dataset Report</h1>
  <p class="boundary">Static research dataset report only. No trading signal, ranking, prediction, execution instruction, profitability claim, or financial advice.</p>

  <section class="card">
    <h2>Executive Summary</h2>
    <ul>{_summary_bullets(summary)}</ul>
  </section>

  <section class="card">
    <h2>Dataset coverage</h2>
    <div class="grid">
      <div class="metric">Status<strong><span class="badge {_status_class(summary.get('status'))}">{_html_text(summary.get('status'))}</span></strong></div>
      <div class="metric">Assets<strong>{_html_text(dataset.get('asset_count'))}</strong></div>
      <div class="metric">Timeframes<strong>{_html_text(', '.join(str(item) for item in _as_list(dataset.get('timeframes'))))}</strong></div>
      <div class="metric">Markets<strong>{_html_text(', '.join(str(item) for item in _as_list(dataset.get('market_types'))))}</strong></div>
      <div class="metric">Primary timeframe<strong>{_html_text(dataset.get('primary_timeframe'))}</strong></div>
      <div class="metric">Refresh seconds<strong>{_html_text(dataset.get('refresh_seconds'))}</strong></div>
    </div>
    <p class="note">Companion machine-readable summary: <a href="{_html_text(summary_href)}">research_summary.json</a>.</p>
  </section>

  <section class="card">
    <h2>Market microstructure metrics</h2>
    <p class="note">Rows describe generated composite OHLCV and public orderbook ladder fields. They are audit metrics, not asset rankings.</p>
    <table>
      <thead><tr><th>Asset</th><th>Timeframe</th><th>Market</th><th>OHLCV status</th><th>Latest close</th><th>Dispersion</th><th>Book status</th><th>Bid/ask depth</th><th>Imbalance</th></tr></thead>
      <tbody>{_microstructure_table(microstructure_rows)}</tbody>
    </table>
  </section>

  <section class="card">
    <h2>LFX-2 alignment contract</h2>
    <p class="note">{_html_text(lfx_alignment.get("source"))} {_html_text(lfx_alignment.get("boundary"))}</p>
    <table>
      <thead><tr><th>Display row</th><th>Question answered</th><th>Artifact basis</th><th>Output fields</th></tr></thead>
      <tbody>{_lfx_contract_table(_as_list(lfx_alignment.get("display_contract")))}</tbody>
    </table>
  </section>

  <section class="card">
    <h2>LFX mission-control artifact readout</h2>
    <p class="note">Rows translate generated public artifacts into a shareable monitor-only readout. They are evidence review text, not ranking, forecast, or execution guidance.</p>
    <table>
      <thead><tr><th>Asset</th><th>Timeframe</th><th>Market</th><th>Display row</th><th>Current readout</th><th>Evidence note</th><th>Basis</th></tr></thead>
      <tbody>{_mission_control_table(mission_rows)}</tbody>
    </table>
  </section>

  <section class="card">
    <h2>Observed zone evidence</h2>
    <p class="note">Observed ranges are public orderbook bucket diagnostics. They do not prove hidden liquidity or future price reaction.</p>
    <table>
      <thead><tr><th>Asset</th><th>Timeframe</th><th>Market</th><th>Evidence mix</th><th>Nearest bid concentration</th><th>Nearest ask concentration</th><th>Next evidence check</th><th>Limitation</th></tr></thead>
      <tbody>{_zone_table(zone_rows)}</tbody>
    </table>
  </section>

  <section class="card">
    <h2>Public demo artifacts</h2>
    <p class="note">These JSON files are the reproducible source artifacts behind the report.</p>
    <table>
      <thead><tr><th>Artifact</th><th>Bytes</th><th>Type</th></tr></thead>
      <tbody>{_artifact_table(artifacts, report_file, artifact_root)}</tbody>
    </table>
  </section>

  <section class="card">
    <h2>Caveats and assumptions</h2>
    <pre>{_json_block(summary.get("limitations"))}</pre>
  </section>
</main>
</body>
</html>
"""
    return html


def assert_no_forbidden_research_terms(html: str) -> None:
    upper = html.upper()
    matched = [
        term
        for term in _FORBIDDEN_RESEARCH_TERMS
        if re.search(rf"(?<![A-Z0-9_]){re.escape(term)}(?![A-Z0-9_])", upper)
    ]
    if matched:
        raise ValueError(f"FORBIDDEN_RESEARCH_TERM: {', '.join(matched)}")


def write_research_report(artifact_root: str | Path, out_file: str | Path, summary_file: str | Path) -> dict[str, Any]:
    root = Path(artifact_root)
    report_file = Path(out_file)
    summary_path = Path(summary_file)
    summary = build_research_summary(root)
    html = _render_html(summary, report_file, summary_path)
    assert_no_forbidden_research_terms(html)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    report_file.write_text(html, encoding="utf-8")

    return {
        "status": summary.get("status", "ERROR"),
        "artifact_root": str(root),
        "report_path": str(report_file),
        "summary_path": str(summary_path),
        "asset_count": summary.get("dataset", {}).get("asset_count"),
        "microstructure_rows": len(_as_list(summary.get("market_microstructure_metrics"))),
        "observed_zone_rows": len(_as_list(summary.get("observed_zone_evidence"))),
        "errors": summary.get("errors", []),
        "warnings": summary.get("warnings", []),
        "boundaries": [NO_SIGNAL_BOUNDARY],
    }
