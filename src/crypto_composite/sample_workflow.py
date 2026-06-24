from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from crypto_composite.artifact_quality import score_artifact_root
from crypto_composite.artifact_report import write_static_report
from crypto_composite.artifact_validator import validate_artifact_root
from crypto_composite.dashboard import write_dashboard_export

SAMPLE_ARTIFACT_ROOT = "examples/sample_artifacts"
SAMPLE_REPORT_OUT_DIR = "sample-report"
NO_SIGNAL_BOUNDARY = "Sample artifact workflow only; no trading signal, execution instruction, prediction, or financial advice."


def _relative_artifact_base_url(artifact_root: Path, out_dir: Path) -> str:
    return Path(os.path.relpath(artifact_root.resolve(), start=out_dir.resolve())).as_posix()


def _status_from_parts(parts: list[dict[str, Any]]) -> str:
    statuses = {str(part.get("status", "ERROR")).upper() for part in parts}
    if "ERROR" in statuses:
        return "ERROR"
    if "WARN" in statuses:
        return "WARN"
    return "OK"


def run_sample_report(
    artifact_root: str | Path = SAMPLE_ARTIFACT_ROOT,
    out_dir: str | Path = SAMPLE_REPORT_OUT_DIR,
    artifact_base_url: str | None = None,
) -> dict[str, Any]:
    """Validate checked-in sample artifacts and write shareable inspection HTML.

    This workflow is intentionally offline. It reads an existing artifact root,
    runs the current validator and quality scorer, and writes HTML inspection
    files. It does not fetch exchange data, call private APIs, create orders,
    rank assets, or generate trading advice.
    """
    root = Path(artifact_root)
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    report_path = target_dir / "artifact_report.html"
    dashboard_path = target_dir / "dashboard.html"
    dashboard_artifact_base_url = artifact_base_url
    if dashboard_artifact_base_url is None:
        dashboard_artifact_base_url = _relative_artifact_base_url(root, target_dir)

    validation = validate_artifact_root(root)
    quality = score_artifact_root(root)
    report = write_static_report(root, report_path)
    dashboard = write_dashboard_export(
        artifact_root=root,
        out_file=dashboard_path,
        artifact_base_url=dashboard_artifact_base_url,
    )

    parts = [validation, quality, report, dashboard]
    status = _status_from_parts(parts)
    errors: list[Any] = []
    warnings: list[Any] = []
    for part in parts:
        errors.extend(part.get("errors", []) if isinstance(part.get("errors", []), list) else [])
        warnings.extend(part.get("warnings", []) if isinstance(part.get("warnings", []), list) else [])
        if part.get("status") == "ERROR" and part.get("error"):
            errors.append({"code": "SAMPLE_WORKFLOW_STEP_ERROR", "message": part["error"]})

    return {
        "status": status,
        "artifact_root": str(root),
        "out_dir": str(target_dir),
        "report_path": str(report_path),
        "dashboard_path": str(dashboard_path),
        "artifact_base_url": dashboard_artifact_base_url,
        "validation": validation,
        "quality": quality,
        "report": report,
        "dashboard": dashboard,
        "errors": errors,
        "warnings": warnings,
        "boundaries": [NO_SIGNAL_BOUNDARY],
    }
