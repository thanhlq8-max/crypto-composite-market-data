from __future__ import annotations

from pathlib import Path
from time import monotonic, sleep
from typing import Any, Callable

from crypto_composite.artifact_quality import write_quality_score
from crypto_composite.artifact_validator import validate_artifact_root
from crypto_composite.dashboard import write_dashboard_export
from crypto_composite.dashboard_profile import DashboardProfileError, build_dashboard_profile, write_dashboard_profile
from crypto_composite.universe import run_universe


class DashboardRefreshError(ValueError):
    """Raised when dashboard refresh inputs are incomplete or inconsistent."""


def _require_non_empty_strings(name: str, values: list[str]) -> list[str]:
    cleaned = [item.strip() for item in values if isinstance(item, str) and item.strip()]
    if not cleaned:
        raise DashboardRefreshError(f"DASHBOARD_REFRESH_{name.upper()}_REQUIRED")
    return cleaned


def _require_positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DashboardRefreshError(f"DASHBOARD_REFRESH_{name.upper()}_INTEGER_REQUIRED")
    if value <= 0:
        raise DashboardRefreshError(f"DASHBOARD_REFRESH_{name.upper()}_POSITIVE_REQUIRED")
    return value


def _require_positive_number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DashboardRefreshError(f"DASHBOARD_REFRESH_{name.upper()}_NUMBER_REQUIRED")
    number = float(value)
    if number <= 0:
        raise DashboardRefreshError(f"DASHBOARD_REFRESH_{name.upper()}_POSITIVE_REQUIRED")
    return number


def _require_text(name: str, value: str | Path) -> str:
    text = str(value).strip()
    if not text:
        raise DashboardRefreshError(f"DASHBOARD_REFRESH_{name.upper()}_REQUIRED")
    return text


def _cycle_status(parts: list[dict[str, Any]], universe_errors: Any) -> str:
    if isinstance(universe_errors, list) and universe_errors:
        return "ERROR"
    statuses = {str(part.get("status", "ERROR")).upper() for part in parts}
    return "ERROR" if "ERROR" in statuses else "OK"


def run_dashboard_refresh(
    *,
    assets: list[str],
    venues: list[str],
    market_types: list[str],
    timeframes: list[str],
    primary_timeframe: str,
    refresh_seconds: int,
    limit: int,
    depth: int,
    out_dir: str | Path,
    dashboard_file: str | Path,
    artifact_base_url: str,
    bucket_size: float,
    max_cycles: int | None = None,
    on_cycle: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Regenerate explicit universe artifacts and a static dashboard on a fixed cadence."""
    cleaned_assets = _require_non_empty_strings("assets", assets)
    cleaned_venues = _require_non_empty_strings("venues", venues)
    cleaned_market_types = _require_non_empty_strings("market_types", market_types)
    cleaned_timeframes = _require_non_empty_strings("timeframes", timeframes)
    seconds = _require_positive_int("refresh_seconds", refresh_seconds)
    cycle_limit = None if max_cycles is None else _require_positive_int("max_cycles", max_cycles)
    row_limit = _require_positive_int("limit", limit)
    book_depth = _require_positive_int("depth", depth)
    price_bucket = _require_positive_number("bucket_size", bucket_size)
    dashboard_target = _require_text("dashboard_file", dashboard_file)
    base_url = _require_text("artifact_base_url", artifact_base_url)
    try:
        build_dashboard_profile(
            primary_timeframe=primary_timeframe,
            timeframes=cleaned_timeframes,
            refresh_seconds=seconds,
        )
    except DashboardProfileError as exc:
        raise DashboardRefreshError(str(exc)) from exc

    root = Path(out_dir)
    cycles: list[dict[str, Any]] = []

    while cycle_limit is None or len(cycles) < cycle_limit:
        cycle_number = len(cycles) + 1
        started = monotonic()
        try:
            universe_summary = run_universe(
                assets=cleaned_assets,
                venues=cleaned_venues,
                market_types=cleaned_market_types,
                timeframes=cleaned_timeframes,
                limit=row_limit,
                depth=book_depth,
                out_dir=root,
                bucket_size=price_bucket,
            )
            profile = write_dashboard_profile(
                root,
                primary_timeframe=primary_timeframe,
                timeframes=cleaned_timeframes,
                refresh_seconds=seconds,
            )
            validation = validate_artifact_root(root)
            quality = write_quality_score(root)
            dashboard = write_dashboard_export(
                artifact_root=root,
                out_file=dashboard_target,
                artifact_base_url=base_url,
            )
            status = _cycle_status([profile, validation, quality, dashboard], universe_summary.get("errors"))
            cycle = {
                "cycle": cycle_number,
                "status": status,
                "asset_count": universe_summary.get("asset_count"),
                "timeframes": universe_summary.get("timeframes"),
                "profile_path": profile["profile_path"],
                "dashboard_path": dashboard.get("dashboard_path"),
                "validation_status": validation.get("status"),
                "quality_status": quality.get("status"),
                "quality_score": quality.get("quality_score"),
                "quality_grade": quality.get("quality_grade"),
                "errors": universe_summary.get("errors", []),
            }
        except Exception as exc:
            cycle = {
                "cycle": cycle_number,
                "status": "ERROR",
                "error": str(exc),
            }
            cycles.append(cycle)
            if on_cycle is not None:
                on_cycle(cycle)
            return {
                "status": "ERROR",
                "cycles_completed": len(cycles),
                "refresh_seconds": seconds,
                "out_dir": str(root),
                "dashboard_file": dashboard_target,
                "last_cycle": cycle,
                "cycles": cycles,
            }

        cycles.append(cycle)
        if on_cycle is not None:
            on_cycle(cycle)
        if cycle["status"] == "ERROR":
            break
        if cycle_limit is not None and len(cycles) >= cycle_limit:
            break
        remaining = seconds - (monotonic() - started)
        if remaining > 0:
            sleep(remaining)

    last_cycle = cycles[-1] if cycles else None
    return {
        "status": last_cycle["status"] if last_cycle else "ERROR",
        "cycles_completed": len(cycles),
        "refresh_seconds": seconds,
        "out_dir": str(root),
        "dashboard_file": dashboard_target,
        "last_cycle": last_cycle,
        "cycles": cycles,
    }
