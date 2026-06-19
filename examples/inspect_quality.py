from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from crypto_composite.artifact_quality import score_artifact_root
from crypto_composite.artifact_validator import validate_artifact_root


BOUNDARY = "Artifact inspection only; no trading signal, execution instruction, or financial advice."


def build_artifact_summary(artifact_root: str | Path) -> dict[str, Any]:
    root = Path(artifact_root)
    validation = validate_artifact_root(root)
    quality = score_artifact_root(root)

    assets = []
    asset_scores = quality.get("asset_scores", {})
    if isinstance(asset_scores, dict):
        for asset, item in sorted(asset_scores.items()):
            if not isinstance(item, dict):
                continue
            timeframes = item.get("timeframes", {})
            assets.append(
                {
                    "asset": asset,
                    "quality_score": item.get("quality_score"),
                    "quality_grade": item.get("quality_grade"),
                    "timeframes": sorted(timeframes) if isinstance(timeframes, dict) else [],
                }
            )

    return {
        "status": quality.get("status"),
        "artifact_root": str(root),
        "mode": quality.get("mode"),
        "assets_checked": quality.get("assets_checked"),
        "quality_score": quality.get("quality_score"),
        "quality_grade": quality.get("quality_grade"),
        "assets": assets,
        "validation_errors": validation.get("errors", []),
        "warnings": quality.get("warnings", []),
        "boundaries": [BOUNDARY],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect generated crypto-composite artifacts.")
    parser.add_argument("--artifact-root", required=True, help="Directory containing generated JSON artifacts.")
    args = parser.parse_args(argv)

    summary = build_artifact_summary(args.artifact_root)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["status"] == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
