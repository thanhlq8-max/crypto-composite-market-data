from __future__ import annotations

import json
from pathlib import Path

import pytest

from crypto_composite.dashboard import DashboardInputError, build_artifact_index, load_json_artifact, _safe_json_path


def test_build_artifact_index_lists_json_files(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "run_summary.json").write_text('{"status":"OK"}', encoding="utf-8")
    (tmp_path / "nested" / "data_quality.json").write_text('{"status":"OK"}', encoding="utf-8")
    (tmp_path / "README.md").write_text("ignore", encoding="utf-8")

    index = build_artifact_index(tmp_path)

    assert index["artifact_count"] == 2
    assert index["well_known"]["run_summary.json"] is True
    assert "nested/data_quality.json" in index["artifacts"]


def test_load_json_artifact_reads_payload(tmp_path: Path) -> None:
    artifact = tmp_path / "data_quality.json"
    artifact.write_text(json.dumps({"status": "OK"}), encoding="utf-8")

    assert load_json_artifact(artifact) == {"status": "OK"}


def test_safe_json_path_rejects_path_traversal(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(DashboardInputError, match="ARTIFACT_PATH_OUTSIDE_ROOT"):
        _safe_json_path(tmp_path, "../outside.json")


def test_safe_json_path_rejects_non_json_file(tmp_path: Path) -> None:
    note = tmp_path / "note.txt"
    note.write_text("ignore", encoding="utf-8")

    with pytest.raises(DashboardInputError, match="ARTIFACT_PATH_NOT_JSON"):
        _safe_json_path(tmp_path, "note.txt")
