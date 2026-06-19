from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest

from crypto_composite.dashboard import (
    DashboardBindError,
    DashboardInputError,
    build_artifact_index,
    load_json_artifact,
    serve_dashboard,
    _safe_json_path,
    make_dashboard_handler,
)
from crypto_composite.dashboard_frontend import render_dashboard_html


def test_build_artifact_index_lists_json_files(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "run_summary.json").write_text('{"status":"OK"}', encoding="utf-8")
    (tmp_path / "nested" / "data_quality.json").write_text('{"status":"OK"}', encoding="utf-8")
    (tmp_path / "README.md").write_text("ignore", encoding="utf-8")

    index = build_artifact_index(tmp_path)

    assert index["artifact_count"] == 2
    assert index["well_known"]["run_summary.json"] is True
    assert index["artifacts"] == [
        {
            "path": "nested/data_quality.json",
            "size_bytes": (tmp_path / "nested" / "data_quality.json").stat().st_size,
        },
        {
            "path": "run_summary.json",
            "size_bytes": (tmp_path / "run_summary.json").stat().st_size,
        },
    ]


def test_render_dashboard_html_reads_object_artifact_contract() -> None:
    html = render_dashboard_html()

    assert "Crypto Composite Data Health" in html
    assert 'getJson("/api/artifacts")' in html
    assert "item.path" in html
    assert "item.size_bytes" in html
    assert ">Buy<" not in html
    assert ">Sell<" not in html


def test_dashboard_http_root_serves_html_and_api_serves_objects(tmp_path: Path) -> None:
    artifact = tmp_path / "data_quality.json"
    artifact.write_text('{"15m":{"status":"OK"}}', encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_dashboard_handler(tmp_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        with urlopen(f"http://{host}:{port}/", timeout=5) as response:
            html = response.read().decode("utf-8")
            assert response.status == 200
            assert response.headers["Content-Type"] == "text/html; charset=utf-8"
            assert "Crypto Composite Data Health" in html

        with urlopen(f"http://{host}:{port}/api/artifacts", timeout=5) as response:
            payload = json.loads(response.read())
            assert response.status == 200
            assert payload["artifacts"] == [{"path": "data_quality.json", "size_bytes": artifact.stat().st_size}]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


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


def test_serve_dashboard_reports_bind_failure(monkeypatch, tmp_path: Path) -> None:
    import crypto_composite.dashboard as dashboard_module

    def raise_permission_error(*args, **kwargs):
        raise PermissionError(10013, "forbidden")

    monkeypatch.setattr(dashboard_module, "ThreadingHTTPServer", raise_permission_error)

    with pytest.raises(DashboardBindError, match="DASHBOARD_BIND_FAILED"):
        serve_dashboard(tmp_path, host="127.0.0.1", port=8765)
