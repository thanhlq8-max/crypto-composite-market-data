from __future__ import annotations

import argparse
import json
from typing import Iterable

from crypto_composite.artifact_quality import score_artifact_root, write_quality_score
from crypto_composite.artifact_report import write_static_report
from crypto_composite.artifact_validator import validate_artifact_root
from crypto_composite.dashboard import (
    DEFAULT_DASHBOARD_HOST,
    DEFAULT_DASHBOARD_PORT,
    DashboardBindError,
    serve_dashboard,
    write_dashboard_export,
)
from crypto_composite.pipeline import (
    DEFAULT_ASSET,
    DEFAULT_DEPTH,
    DEFAULT_LIMIT,
    DEFAULT_MARKET_TYPES,
    DEFAULT_TIMEFRAMES,
    DEFAULT_VENUES,
    run_composite,
)
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

    dashboard_export = sub.add_parser("dashboard-export", help="Write Dashboard V2 as static HTML.")
    dashboard_export.add_argument("--artifact-root", required=True, help="Directory containing JSON artifacts.")
    dashboard_export.add_argument("--out-file", required=True, help="Static Dashboard V2 HTML file to write.")
    dashboard_export.add_argument(
        "--artifact-base-url",
        help="Optional relative URL containing JSON artifacts for the static inspector.",
    )

    validate = sub.add_parser("validate-artifacts", help="Validate generated JSON artifact structure.")
    validate.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")

    score = sub.add_parser("score-artifacts", help="Score generated artifact data quality.")
    score.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")
    score.add_argument("--write", action="store_true", help="Write quality_score.json into the artifact root.")

    report = sub.add_parser("report", help="Write a static HTML artifact quality report.")
    report.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")
    report.add_argument("--out-file", required=True, help="HTML report file to write.")

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
    elif args.cmd == "report":
        report_result = write_static_report(args.artifact_root, args.out_file)
        print(json.dumps(report_result, indent=2, sort_keys=True))
        if report_result["status"] == "ERROR":
            parser.exit(1)


if __name__ == "__main__":
    main()
