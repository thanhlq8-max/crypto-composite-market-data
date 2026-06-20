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
