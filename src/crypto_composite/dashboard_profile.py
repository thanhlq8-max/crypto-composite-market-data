from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crypto_composite.utils import write_json


PROFILE_FILENAME = "dashboard_profile.json"
PROFILE_SCHEMA_VERSION = 1
PROFILE_BOUNDARIES = [
    "Dashboard profile metadata only; no trading signal, prediction, ranking, or execution instruction.",
    "Refresh cadence describes artifact regeneration cadence; it does not imply market-data completeness.",
]


class DashboardProfileError(ValueError):
    """Raised when dashboard profile metadata is incomplete or inconsistent."""


def _clean_timeframes(timeframes: list[str]) -> list[str]:
    cleaned = [item.strip() for item in timeframes if isinstance(item, str) and item.strip()]
    if not cleaned:
        raise DashboardProfileError("DASHBOARD_PROFILE_TIMEFRAMES_REQUIRED")
    return cleaned


def build_dashboard_profile(
    *,
    primary_timeframe: str,
    timeframes: list[str],
    refresh_seconds: int,
) -> dict[str, Any]:
    """Build explicit dashboard profile metadata for an artifact root."""
    primary = primary_timeframe.strip() if isinstance(primary_timeframe, str) else ""
    if not primary:
        raise DashboardProfileError("DASHBOARD_PROFILE_PRIMARY_TIMEFRAME_REQUIRED")
    cleaned_timeframes = _clean_timeframes(timeframes)
    if primary not in cleaned_timeframes:
        raise DashboardProfileError(
            "DASHBOARD_PROFILE_PRIMARY_TIMEFRAME_NOT_IN_TIMEFRAMES:"
            f"primary_timeframe={primary!r}:timeframes={cleaned_timeframes!r}"
        )
    if isinstance(refresh_seconds, bool) or not isinstance(refresh_seconds, int):
        raise DashboardProfileError("DASHBOARD_PROFILE_REFRESH_SECONDS_INTEGER_REQUIRED")
    if refresh_seconds <= 0:
        raise DashboardProfileError("DASHBOARD_PROFILE_REFRESH_SECONDS_POSITIVE_REQUIRED")
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "primary_timeframe": primary,
        "timeframes": cleaned_timeframes,
        "refresh_seconds": refresh_seconds,
        "boundaries": PROFILE_BOUNDARIES,
    }


def write_dashboard_profile(
    artifact_root: str | Path,
    *,
    primary_timeframe: str,
    timeframes: list[str],
    refresh_seconds: int,
) -> dict[str, Any]:
    """Write explicit dashboard profile metadata into an artifact root."""
    root = Path(artifact_root)
    profile = build_dashboard_profile(
        primary_timeframe=primary_timeframe,
        timeframes=timeframes,
        refresh_seconds=refresh_seconds,
    )
    path = root / PROFILE_FILENAME
    write_json(path, profile)
    return {
        "status": "OK",
        "profile_path": str(path),
        "profile": profile,
    }


def read_dashboard_profile(artifact_root: str | Path) -> dict[str, Any] | None:
    """Read optional dashboard profile metadata from an artifact root."""
    path = Path(artifact_root) / PROFILE_FILENAME
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None
