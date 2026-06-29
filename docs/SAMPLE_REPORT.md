# Sample artifact report workflow

`crypto-composite sample-report` is an offline first-run workflow for source checkouts.

It reads an existing artifact root, validates the artifact structure, computes the artifact quality score, and writes two local HTML inspection files:

```text
sample-report/artifact_report.html
sample-report/dashboard.html
```

The default input is the checked-in `examples/sample_artifacts` directory.
That fixture includes a dashboard profile with primary timeframe `15m`,
multi-timeframe filters `5m,15m,1h`, and a 60-second refresh metadata cadence.

The command does not fetch live exchange data. It is meant to let a new user inspect the project output shape before running public exchange connectors.

## Usage

From a cloned repository:

```bash
crypto-composite sample-report
```

Custom output directory:

```bash
crypto-composite sample-report \
  --artifact-root examples/sample_artifacts \
  --out-dir sample-report
```

Custom artifact link base for the static dashboard:

```bash
crypto-composite sample-report \
  --artifact-root examples/sample_artifacts \
  --out-dir site \
  --artifact-base-url artifacts
```

The command prints JSON with:

- validation result;
- quality score result;
- static artifact report path;
- static dashboard path;
- public-data-only boundary text.

## GitHub Pages demo use

The manual GitHub Pages workflow copies checked-in sample artifacts into a staging directory and runs this command against the copied artifact tree:

```bash
crypto-composite sample-report \
  --artifact-root _site/artifacts \
  --out-dir _site \
  --artifact-base-url artifacts
```

It then copies `_site/artifact_report.html` to `_site/index.html` as the Pages landing page.

See [GITHUB_PAGES_DEMO.md](GITHUB_PAGES_DEMO.md) for the full deployment and local reproduction flow.

## Boundary

This workflow is artifact inspection only. It does not create trading signals, execution instructions, predictions, rankings, position sizing, private API calls, or financial advice.
