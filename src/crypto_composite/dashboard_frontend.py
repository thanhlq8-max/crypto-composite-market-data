from __future__ import annotations

import json
from importlib import resources
from typing import Any


def _embedded_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).replace("<", "\\u003c")


def _load_template() -> str:
    return (resources.files("crypto_composite.templates") / "dashboard.html").read_text(
        encoding="utf-8"
    )


def render_dashboard_html(
    embedded_snapshot: dict[str, Any] | None = None,
    embedded_index: dict[str, Any] | None = None,
    artifact_base_url: str | None = None,
) -> str:
    html = _load_template()
    return (
        html.replace("__EMBEDDED_SNAPSHOT__", _embedded_json(embedded_snapshot))
        .replace("__EMBEDDED_INDEX__", _embedded_json(embedded_index))
        .replace("__ARTIFACT_BASE_URL__", _embedded_json(artifact_base_url))
    )
