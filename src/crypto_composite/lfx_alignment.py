from __future__ import annotations

from typing import Any


LFX_ALIGNMENT_SOURCE = (
    "LFX-2 v8.1-D Counterflow Route-Origin Text, adapted to public crypto artifact inspection."
)

_DISPLAY_CONTRACT = (
    {
        "panel": "MM Mission",
        "question": "What public-artifact job is most important for this view?",
        "artifact_basis": ["artifact status", "zone evidence mix", "public-depth context"],
        "output_fields": ["lfx_mission_control.rows"],
    },
    {
        "panel": "TRADER Mode",
        "question": "Which review posture fits the current artifact quality?",
        "artifact_basis": ["OHLCV status", "book status", "observed zone availability"],
        "output_fields": ["lfx_mission_control.rows"],
    },
    {
        "panel": "NEXT Scenario",
        "question": "What evidence should be checked after the next refresh?",
        "artifact_basis": ["OHLCV status", "book status", "zone evidence mix", "refresh profile"],
        "output_fields": ["monitoring_brief.next_evidence_check", "zone_readout.next_check", "lfx_mission_control.rows"],
    },
    {
        "panel": "DID / Past",
        "question": "What already happened in the generated artifact?",
        "artifact_basis": ["latest two composite bars", "observed close change", "bar count"],
        "output_fields": ["monitoring_brief.past", "lfx_mission_control.rows"],
    },
    {
        "panel": "DOING / Now",
        "question": "What public-data context is visible now?",
        "artifact_basis": ["latest composite bar", "public orderbook ladder", "nearest bid/ask concentration"],
        "output_fields": ["monitoring_brief.now", "observed_zones", "lfx_mission_control.rows"],
    },
    {
        "panel": "KEY Zones",
        "question": "Which practical public-depth ranges deserve review?",
        "artifact_basis": ["top depth bucket", "maximum vacuum bucket", "evidence grade", "distance to reference"],
        "output_fields": ["observed_zones", "mtf_zone_map", "lfx_mission_control.rows"],
    },
    {
        "panel": "INV / Release",
        "question": "What public imbalance and reference context is visible?",
        "artifact_basis": ["depth imbalance", "nearest bid/ask concentration", "price dispersion"],
        "output_fields": ["monitoring_brief.now", "lfx_mission_control.rows"],
    },
    {
        "panel": "Confidence / Risk",
        "question": "How reliable is the current artifact context?",
        "artifact_basis": ["coverage", "venue count", "price dispersion", "single-snapshot limitation"],
        "output_fields": ["monitoring_brief.confidence_risk", "methodology", "lfx_mission_control.rows"],
    },
)

_PRACTICAL_ZONE_RULES = (
    "Render practical concentration and maximum-vacuum public-depth ranges instead of raw zone spam.",
    "Prefer M15 as the primary operating timeframe when the artifact profile declares it.",
    "Use M5, M15, and H1 as descriptive multi-timeframe context when present.",
    "Treat H4/D1 concepts as structural-only unless generated artifacts explicitly provide those timeframes.",
    "Use density or confluence wording as reference context only; it must not create a route, target, or signal.",
    "Use counterflow or route-origin wording as evidence-check text only; public artifacts do not prove private flow.",
    "Keep NEXT wording conditional and evidence-focused, not predictive.",
    "Use operating language and review checklists instead of trade-command language.",
)

_FORBIDDEN_SEMANTICS = (
    "No BUY or SELL command.",
    "No entry, exit, stop-loss, take-profit, or position-sizing instruction.",
    "No asset ranking, prediction, strategy backtest, or automated execution.",
    "No route or target creator unless generated public artifacts explicitly contain that evidence.",
    "No claim of real market-maker inventory, real retail positioning, hidden liquidity, or future price reaction.",
    "No RSI, overbought/oversold, or mean-reversion-by-distance logic.",
)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def build_lfx_alignment(profile: dict[str, Any] | None) -> dict[str, Any]:
    """Describe the LFX-2 monitor-only contract applied to public artifacts."""
    profile_obj = profile if isinstance(profile, dict) else {}
    return {
        "source": LFX_ALIGNMENT_SOURCE,
        "status": "ADAPTED_MONITOR_ONLY",
        "profile": {
            "primary_timeframe": profile_obj.get("primary_timeframe"),
            "timeframes": _string_list(profile_obj.get("timeframes")),
            "refresh_seconds": profile_obj.get("refresh_seconds"),
        },
        "display_contract": [
            {
                "panel": item["panel"],
                "question": item["question"],
                "artifact_basis": list(item["artifact_basis"]),
                "output_fields": list(item["output_fields"]),
            }
            for item in _DISPLAY_CONTRACT
        ],
        "practical_zone_rules": list(_PRACTICAL_ZONE_RULES),
        "forbidden_semantics": list(_FORBIDDEN_SEMANTICS),
        "boundary": (
            "LFX-style behavior surveillance is implemented as public artifact review only; "
            "it does not infer real market-maker intent or issue trade instructions."
        ),
    }
