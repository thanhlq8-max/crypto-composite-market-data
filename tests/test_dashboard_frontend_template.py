"""The dashboard HTML template ships as package data and renders unchanged."""

from __future__ import annotations

from importlib import resources

from crypto_composite.dashboard_frontend import render_dashboard_html


def test_template_ships_as_package_resource() -> None:
    template = (resources.files("crypto_composite.templates") / "dashboard.html").read_text(
        encoding="utf-8"
    )
    assert template.startswith("<!doctype html>")
    assert template.rstrip().endswith("</html>")
    for placeholder in ("__EMBEDDED_SNAPSHOT__", "__EMBEDDED_INDEX__", "__ARTIFACT_BASE_URL__"):
        assert placeholder in template


def test_render_replaces_every_placeholder() -> None:
    html = render_dashboard_html(
        embedded_snapshot={"assets": [{"asset": "BTC-USDT"}]},
        embedded_index={"artifact_count": 0},
        artifact_base_url="https://example.test/artifacts",
    )
    assert "__EMBEDDED_SNAPSHOT__" not in html
    assert "__EMBEDDED_INDEX__" not in html
    assert "__ARTIFACT_BASE_URL__" not in html
    assert '"asset":"BTC-USDT"' in html
    assert '"https://example.test/artifacts"' in html


def test_render_defaults_embed_null_payloads() -> None:
    html = render_dashboard_html()
    assert "const embeddedSnapshot = null;" in html
    assert "const embeddedIndex = null;" in html


def test_embedded_json_escapes_html_open_brackets() -> None:
    # A '<' inside embedded JSON could open a tag (e.g. close the script
    # element early); it must be escaped, so the raw sequence never appears.
    html = render_dashboard_html(embedded_snapshot={"note": "</script><b>"})
    assert '"note":"</script>' not in html
    assert '"note":"\\u003c/script>\\u003cb>"' in html
