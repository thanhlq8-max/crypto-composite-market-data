from __future__ import annotations

from crypto_composite.lfx_alignment import build_lfx_alignment


def test_build_lfx_alignment_maps_monitor_only_contract() -> None:
    alignment = build_lfx_alignment(
        {
            "primary_timeframe": "15m",
            "timeframes": ["5m", "15m", "1h"],
            "refresh_seconds": 60,
        }
    )

    assert alignment["status"] == "ADAPTED_MONITOR_ONLY"
    assert alignment["profile"] == {
        "primary_timeframe": "15m",
        "timeframes": ["5m", "15m", "1h"],
        "refresh_seconds": 60,
    }
    assert [row["panel"] for row in alignment["display_contract"]] == [
        "MM Mission",
        "TRADER Mode",
        "NEXT Scenario",
        "DID / Past",
        "DOING / Now",
        "KEY Zones",
        "INV / Release",
        "Confidence / Risk",
    ]
    assert "v8.1-D" in alignment["source"]
    assert any("M15" in rule for rule in alignment["practical_zone_rules"])
    assert any("counterflow" in rule.lower() for rule in alignment["practical_zone_rules"])
    assert any("No BUY or SELL command." == rule for rule in alignment["forbidden_semantics"])
    assert "real market-maker intent" in alignment["boundary"]
