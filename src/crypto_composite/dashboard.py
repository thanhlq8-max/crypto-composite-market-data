from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


DEFAULT_DASHBOARD_HOST = "127.0.0.1"
DEFAULT_DASHBOARD_PORT = 18080


class DashboardInputError(ValueError):
    """Raised when dashboard artifact input is invalid."""


class DashboardBindError(OSError):
    """Raised when the local dashboard server cannot bind to the requested socket."""


def _safe_root(path: str | Path) -> Path:
    root = Path(path).expanduser().resolve()
    if not root.exists():
        raise DashboardInputError(f"ARTIFACT_ROOT_NOT_FOUND:{root}")
    if not root.is_dir():
        raise DashboardInputError(f"ARTIFACT_ROOT_NOT_DIRECTORY:{root}")
    return root


def _safe_json_path(root: Path, relative_path: str) -> Path:
    candidate = (root / unquote(relative_path)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise DashboardInputError("ARTIFACT_PATH_OUTSIDE_ROOT") from exc
    if candidate.suffix.lower() != ".json":
        raise DashboardInputError("ARTIFACT_PATH_NOT_JSON")
    if not candidate.exists() or not candidate.is_file():
        raise DashboardInputError(f"ARTIFACT_PATH_NOT_FOUND:{relative_path}")
    return candidate


def load_json_artifact(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_artifact_index(artifact_root: str | Path) -> dict[str, Any]:
    """Build a small JSON-file index for a local artifact directory.

    The dashboard index is intentionally read-only. It lists JSON artifacts and a
    few well-known files so local UIs can inspect data quality without adding
    trading signal semantics.
    """
    root = _safe_root(artifact_root)
    json_files = sorted(path for path in root.rglob("*.json") if path.is_file())
    artifacts = [str(path.relative_to(root)).replace("\\", "/") for path in json_files]
    well_known = {
        name: name in artifacts
        for name in [
            "run_summary.json",
            "data_quality.json",
            "universe_summary.json",
            "composite_ohlcv.json",
            "composite_orderbook_ladder.json",
        ]
    }
    return {
        "artifact_root": str(root),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "well_known": well_known,
        "boundaries": [
            "Read-only local artifact API.",
            "No trading signals, order execution, position sizing, or financial advice.",
        ],
    }


def make_dashboard_handler(artifact_root: str | Path):
    root = _safe_root(artifact_root)

    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "CryptoCompositeDashboard/0.3"

        def _write_json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/" or parsed.path == "/api/health":
                    self._write_json(200, {"status": "OK", "service": "crypto-composite-dashboard"})
                    return
                if parsed.path == "/api/artifacts":
                    self._write_json(200, build_artifact_index(root))
                    return
                if parsed.path == "/api/artifact":
                    query = parse_qs(parsed.query)
                    artifact_path = query.get("path", [""])[0]
                    if not artifact_path:
                        raise DashboardInputError("ARTIFACT_PATH_REQUIRED")
                    self._write_json(200, load_json_artifact(_safe_json_path(root, artifact_path)))
                    return
                self._write_json(404, {"error": "NOT_FOUND", "path": parsed.path})
            except DashboardInputError as exc:
                self._write_json(400, {"error": str(exc)})
            except json.JSONDecodeError as exc:
                self._write_json(500, {"error": "ARTIFACT_JSON_DECODE_FAILED", "detail": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
            return

    return DashboardHandler


def serve_dashboard(
    artifact_root: str | Path,
    host: str = DEFAULT_DASHBOARD_HOST,
    port: int = DEFAULT_DASHBOARD_PORT,
) -> None:
    """Serve a read-only local dashboard API over stdlib HTTP."""
    handler = make_dashboard_handler(artifact_root)
    try:
        server = ThreadingHTTPServer((host, port), handler)
    except OSError as exc:
        raise DashboardBindError(
            "DASHBOARD_BIND_FAILED:"
            f"host={host}:port={port}:"
            "try a different local port, for example --port 18081 or --port 19080"
        ) from exc

    print(f"STATUS: OK dashboard=http://{host}:{port} artifact_root={Path(artifact_root).resolve()}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
