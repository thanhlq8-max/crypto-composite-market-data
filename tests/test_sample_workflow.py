from __future__ import annotations

from pathlib import Path

from crypto_composite import sample_workflow


def test_run_sample_report_uses_existing_artifact_tools(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []

    def fake_validate_artifact_root(root: object) -> dict:
        calls.append(("validate", root))
        return {"status": "OK", "errors": [], "warnings": []}

    def fake_score_artifact_root(root: object) -> dict:
        calls.append(("score", root))
        return {"status": "OK", "quality_score": 91.0, "quality_grade": "A", "errors": [], "warnings": []}

    def fake_write_static_report(root: object, out_file: object) -> dict:
        calls.append(("report", out_file))
        return {"status": "OK", "report_path": str(out_file), "errors": [], "warnings": []}

    def fake_write_dashboard_export(**kwargs: object) -> dict:
        calls.append(("dashboard", kwargs["out_file"]))
        return {"status": "OK", "dashboard_path": str(kwargs["out_file"]), "errors": [], "warnings": []}

    monkeypatch.setattr(sample_workflow, "validate_artifact_root", fake_validate_artifact_root)
    monkeypatch.setattr(sample_workflow, "score_artifact_root", fake_score_artifact_root)
    monkeypatch.setattr(sample_workflow, "write_static_report", fake_write_static_report)
    monkeypatch.setattr(sample_workflow, "write_dashboard_export", fake_write_dashboard_export)

    result = sample_workflow.run_sample_report(
        artifact_root="examples/sample_artifacts",
        out_dir=tmp_path,
        artifact_base_url="artifacts",
    )

    assert result["status"] == "OK"
    assert result["artifact_base_url"] == "artifacts"
    assert result["report_path"] == str(tmp_path / "artifact_report.html")
    assert result["dashboard_path"] == str(tmp_path / "dashboard.html")
    assert result["errors"] == []
    assert [name for name, _ in calls] == ["validate", "score", "report", "dashboard"]


def test_run_sample_report_returns_error_when_a_step_fails(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sample_workflow, "validate_artifact_root", lambda root: {"status": "ERROR", "errors": [{"code": "BAD"}], "warnings": []})
    monkeypatch.setattr(sample_workflow, "score_artifact_root", lambda root: {"status": "ERROR", "errors": [{"code": "BAD"}], "warnings": []})
    monkeypatch.setattr(sample_workflow, "write_static_report", lambda root, out_file: {"status": "ERROR", "errors": [{"code": "BAD"}], "warnings": []})
    monkeypatch.setattr(
        sample_workflow,
        "write_dashboard_export",
        lambda **kwargs: {"status": "ERROR", "error": "DASHBOARD_FAILED", "errors": [], "warnings": []},
    )

    result = sample_workflow.run_sample_report(out_dir=tmp_path)

    assert result["status"] == "ERROR"
    assert {item.get("code") for item in result["errors"] if isinstance(item, dict)} == {"BAD", "SAMPLE_WORKFLOW_STEP_ERROR"}
