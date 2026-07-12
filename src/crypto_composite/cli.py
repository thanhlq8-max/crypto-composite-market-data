from __future__ import annotations

import argparse
import json
from typing import Iterable

from crypto_composite.artifact_csv import write_composite_ohlcv_csv
from crypto_composite.artifact_parquet import ParquetDependencyError, write_composite_ohlcv_parquet
from crypto_composite.stream_depth import StreamDependencyError, run_stream_depth
from crypto_composite.artifact_quality import score_artifact_root, write_quality_score
from crypto_composite.artifact_report import write_static_report
from crypto_composite.sample_workflow import run_sample_report
from crypto_composite.artifact_validator import validate_artifact_root
from crypto_composite.dashboard import (
    DEFAULT_DASHBOARD_HOST,
    DEFAULT_DASHBOARD_PORT,
    DashboardBindError,
    serve_dashboard,
    write_dashboard_export,
)
from crypto_composite.dashboard_profile import DashboardProfileError, write_dashboard_profile
from crypto_composite.dashboard_refresh import DashboardRefreshError, run_dashboard_refresh
from crypto_composite.pipeline import (
    DEFAULT_ASSET,
    DEFAULT_DEPTH,
    DEFAULT_LIMIT,
    DEFAULT_MARKET_TYPES,
    DEFAULT_TIMEFRAMES,
    DEFAULT_VENUES,
    run_composite,
)
from crypto_composite.research_report import write_research_report
from crypto_composite.universe import run_universe


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _join(values: Iterable[str]) -> str:
    return ",".join(values)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="crypto-composite",
        description="Build public multi-exchange crypto market-data composite artifacts.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Fetch public data and write composite artifacts.")
    run.add_argument("--asset", default=DEFAULT_ASSET)
    run.add_argument("--venues", default=_join(DEFAULT_VENUES))
    run.add_argument("--market-types", default=_join(DEFAULT_MARKET_TYPES))
    run.add_argument("--timeframes", default=_join(DEFAULT_TIMEFRAMES))
    run.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    run.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    run.add_argument("--out-dir", default="artifacts")
    run.add_argument("--bucket-size", type=float, default=None)

    universe = sub.add_parser("universe", help="Run composite artifacts for an explicit multi-asset universe.")
    universe.add_argument(
        "--assets",
        required=True,
        help="Comma-separated BASE-USDT assets, for example BTC-USDT,ETH-USDT,SOL-USDT.",
    )
    universe.add_argument("--venues", default=_join(DEFAULT_VENUES))
    universe.add_argument("--market-types", default=_join(DEFAULT_MARKET_TYPES))
    universe.add_argument("--timeframes", default=_join(DEFAULT_TIMEFRAMES))
    universe.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    universe.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    universe.add_argument("--out-dir", default="artifacts")
    universe.add_argument("--bucket-size", type=float, default=None)

    dashboard = sub.add_parser("dashboard", help="Serve a read-only local artifact dashboard API.")
    dashboard.add_argument("--artifact-root", default="artifacts", help="Directory containing JSON artifacts.")
    dashboard.add_argument("--host", default=DEFAULT_DASHBOARD_HOST)
    dashboard.add_argument("--port", type=int, default=DEFAULT_DASHBOARD_PORT)

    dashboard_export = sub.add_parser("dashboard-export", help="Write Dashboard V3 as static HTML.")
    dashboard_export.add_argument("--artifact-root", required=True, help="Directory containing JSON artifacts.")
    dashboard_export.add_argument("--out-file", required=True, help="Static Dashboard V3 HTML file to write.")
    dashboard_export.add_argument(
        "--artifact-base-url",
        help="Optional relative URL containing JSON artifacts for the static inspector.",
    )

    dashboard_profile = sub.add_parser("dashboard-profile", help="Write explicit dashboard profile metadata.")
    dashboard_profile.add_argument("--artifact-root", required=True, help="Directory containing JSON artifacts.")
    dashboard_profile.add_argument("--primary-timeframe", required=True, help="Primary dashboard timeframe, for example 15m.")
    dashboard_profile.add_argument("--timeframes", required=True, help="Comma-separated dashboard timeframes.")
    dashboard_profile.add_argument("--refresh-seconds", type=int, required=True, help="Artifact refresh cadence in seconds.")

    dashboard_refresh = sub.add_parser(
        "dashboard-refresh",
        help="Regenerate explicit universe artifacts and a static dashboard on a fixed cadence.",
    )
    dashboard_refresh.add_argument("--assets", required=True, help="Comma-separated BASE-USDT assets.")
    dashboard_refresh.add_argument("--venues", required=True, help="Comma-separated public venues.")
    dashboard_refresh.add_argument("--market-types", required=True, help="Comma-separated market types.")
    dashboard_refresh.add_argument("--timeframes", required=True, help="Comma-separated timeframes.")
    dashboard_refresh.add_argument("--primary-timeframe", required=True, help="Primary dashboard timeframe.")
    dashboard_refresh.add_argument("--refresh-seconds", type=int, required=True, help="Artifact refresh cadence in seconds.")
    dashboard_refresh.add_argument("--limit", type=int, required=True, help="OHLCV bar limit per refresh.")
    dashboard_refresh.add_argument("--depth", type=int, required=True, help="Orderbook depth limit per refresh.")
    dashboard_refresh.add_argument("--bucket-size", type=float, required=True, help="Explicit orderbook ladder bucket size.")
    dashboard_refresh.add_argument("--out-dir", required=True, help="Artifact directory to refresh.")
    dashboard_refresh.add_argument("--dashboard-file", required=True, help="Static dashboard HTML file to write.")
    dashboard_refresh.add_argument("--artifact-base-url", required=True, help="Relative URL for dashboard JSON inspector links.")
    dashboard_refresh.add_argument("--max-cycles", type=int, help="Stop after this many refresh cycles.")

    validate = sub.add_parser("validate-artifacts", help="Validate generated JSON artifact structure.")
    validate.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")

    score = sub.add_parser("score-artifacts", help="Score generated artifact data quality.")
    score.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")
    score.add_argument("--write", action="store_true", help="Write quality_score.json into the artifact root.")

    csv_export = sub.add_parser("export-ohlcv-csv", help="Export composite OHLCV artifacts to a flat CSV file.")
    csv_export.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")
    csv_export.add_argument("--out-file", required=True, help="CSV file to write.")

    parquet_export = sub.add_parser(
        "export-ohlcv-parquet",
        help="Export composite OHLCV artifacts to a flat Parquet file (requires the [parquet] extra).",
    )
    parquet_export.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")
    parquet_export.add_argument("--out-file", required=True, help="Parquet file to write.")

    report = sub.add_parser("report", help="Write a static HTML artifact quality report.")
    report.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")
    report.add_argument("--out-file", required=True, help="HTML report file to write.")

    research_report = sub.add_parser("research-report", help="Write a static research dataset report and JSON summary.")
    research_report.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")
    research_report.add_argument("--out-file", required=True, help="HTML research report file to write.")
    research_report.add_argument("--summary-file", required=True, help="Machine-readable research summary JSON file to write.")

    stream_depth = sub.add_parser(
        "stream-depth",
        help="Watch perp book WebSocket streams and write a zone_lifecycle.json artifact (requires the [stream] extra).",
    )
    stream_depth.add_argument("--asset", default="BTC-USDT", help="BASE-USDT asset, for example BTC-USDT.")
    stream_depth.add_argument("--venues", default="binance,okx,bybit", help="Comma-separated perp venues to stream.")
    stream_depth.add_argument("--duration", type=float, default=120.0, help="Watch window in seconds.")
    stream_depth.add_argument("--sample-interval", type=float, default=1.0, help="Lifecycle sampling interval in seconds.")
    stream_depth.add_argument("--out-dir", default="artifacts", help="Directory for zone_lifecycle.json.")

    sample_report = sub.add_parser("sample-report", help="Validate sample artifacts and write offline HTML inspection files.")
    sample_report.add_argument("--artifact-root", default="examples/sample_artifacts", help="Existing artifact root to inspect.")
    sample_report.add_argument("--out-dir", default="sample-report", help="Directory for generated sample inspection HTML.")
    sample_report.add_argument("--artifact-base-url", help="Optional artifact base URL for dashboard links.")

    args = parser.parse_args()
    if args.cmd == "run":
        result = run_composite(
            asset=args.asset,
            venues=parse_csv(args.venues),
            market_types=parse_csv(args.market_types),
            timeframes=parse_csv(args.timeframes),
            limit=args.limit,
            depth=args.depth,
            out_dir=args.out_dir,
            bucket_size=args.bucket_size,
        )
        summary = result["summary"]
        print(
            "STATUS: OK "
            f"asset={summary['asset']} "
            f"timeframes={','.join(summary['timeframes'])} "
            f"out_dir={args.out_dir}"
        )
    elif args.cmd == "universe":
        summary = run_universe(
            assets=parse_csv(args.assets),
            venues=parse_csv(args.venues),
            market_types=parse_csv(args.market_types),
            timeframes=parse_csv(args.timeframes),
            limit=args.limit,
            depth=args.depth,
            out_dir=args.out_dir,
            bucket_size=args.bucket_size,
        )
        print(
            "STATUS: OK "
            f"assets={summary['asset_count']} "
            f"timeframes={','.join(summary['timeframes'])} "
            f"out_dir={args.out_dir}"
        )
    elif args.cmd == "dashboard":
        try:
            serve_dashboard(artifact_root=args.artifact_root, host=args.host, port=args.port)
        except DashboardBindError as exc:
            parser.exit(2, f"ERROR: {exc}\n")
    elif args.cmd == "dashboard-export":
        export_result = write_dashboard_export(
            artifact_root=args.artifact_root,
            out_file=args.out_file,
            artifact_base_url=args.artifact_base_url,
        )
        print(json.dumps(export_result, indent=2, sort_keys=True))
        if export_result["status"] == "ERROR":
            parser.exit(1)
    elif args.cmd == "dashboard-profile":
        try:
            profile_result = write_dashboard_profile(
                args.artifact_root,
                primary_timeframe=args.primary_timeframe,
                timeframes=parse_csv(args.timeframes),
                refresh_seconds=args.refresh_seconds,
            )
        except DashboardProfileError as exc:
            parser.exit(1, f"ERROR: {exc}\n")
        print(json.dumps(profile_result, indent=2, sort_keys=True))
    elif args.cmd == "dashboard-refresh":
        def _print_cycle(cycle: dict[str, object]) -> None:
            print(
                "STATUS: "
                f"{cycle.get('status')} "
                f"cycle={cycle.get('cycle')} "
                f"dashboard={cycle.get('dashboard_path', 'unavailable')}",
                flush=True,
            )

        try:
            refresh_result = run_dashboard_refresh(
                assets=parse_csv(args.assets),
                venues=parse_csv(args.venues),
                market_types=parse_csv(args.market_types),
                timeframes=parse_csv(args.timeframes),
                primary_timeframe=args.primary_timeframe,
                refresh_seconds=args.refresh_seconds,
                limit=args.limit,
                depth=args.depth,
                out_dir=args.out_dir,
                dashboard_file=args.dashboard_file,
                artifact_base_url=args.artifact_base_url,
                bucket_size=args.bucket_size,
                max_cycles=args.max_cycles,
                on_cycle=_print_cycle,
            )
        except DashboardRefreshError as exc:
            parser.exit(1, f"ERROR: {exc}\n")
        print(json.dumps(refresh_result, indent=2, sort_keys=True))
        if refresh_result["status"] == "ERROR":
            parser.exit(1)
    elif args.cmd == "validate-artifacts":
        validation = validate_artifact_root(args.artifact_root)
        print(json.dumps(validation, indent=2, sort_keys=True))
        if validation["status"] == "ERROR":
            parser.exit(1)
    elif args.cmd == "score-artifacts":
        quality = write_quality_score(args.artifact_root) if args.write else score_artifact_root(args.artifact_root)
        print(json.dumps(quality, indent=2, sort_keys=True))
        if quality["status"] == "ERROR":
            parser.exit(1)
    elif args.cmd == "export-ohlcv-csv":
        export_result = write_composite_ohlcv_csv(args.artifact_root, args.out_file)
        print(json.dumps(export_result, indent=2, sort_keys=True))
        if export_result["status"] == "ERROR":
            parser.exit(1)
    elif args.cmd == "stream-depth":
        try:
            stream_result = run_stream_depth(
                asset=args.asset,
                venues=parse_csv(args.venues),
                duration_s=args.duration,
                sample_interval_s=args.sample_interval,
                out_dir=args.out_dir,
            )
        except StreamDependencyError as exc:
            parser.exit(1, f"{exc}\n")
        print(json.dumps(stream_result, indent=2, sort_keys=True))
    elif args.cmd == "export-ohlcv-parquet":
        try:
            export_result = write_composite_ohlcv_parquet(args.artifact_root, args.out_file)
        except ParquetDependencyError as exc:
            parser.exit(1, f"{exc}\n")
        print(json.dumps(export_result, indent=2, sort_keys=True))
        if export_result["status"] == "ERROR":
            parser.exit(1)
    elif args.cmd == "sample-report":
        sample_result = run_sample_report(
            artifact_root=args.artifact_root,
            out_dir=args.out_dir,
            artifact_base_url=args.artifact_base_url,
        )
        print(json.dumps(sample_result, indent=2, sort_keys=True))
        if sample_result["status"] == "ERROR":
            parser.exit(1)
    elif args.cmd == "report":
        report_result = write_static_report(args.artifact_root, args.out_file)
        print(json.dumps(report_result, indent=2, sort_keys=True))
        if report_result["status"] == "ERROR":
            parser.exit(1)
    elif args.cmd == "research-report":
        research_result = write_research_report(args.artifact_root, args.out_file, args.summary_file)
        print(json.dumps(research_result, indent=2, sort_keys=True))
        if research_result["status"] == "ERROR":
            parser.exit(1)


if __name__ == "__main__":
    main()
