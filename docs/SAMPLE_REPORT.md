# Sample artifact report workflow

`crypto-composite sample-report` is an offline first-run workflow for source checkouts.

It reads the checked-in `examples/sample_artifacts` directory, validates the artifact structure, computes the artifact quality score, and writes two local HTML inspection files:

```text
sample-report/artifact_report.html
sample-report/dashboard.html
```

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

## Boundary

This workflow is artifact inspection only. It does not create trading signals, execution instructions, predictions, position sizing, private API calls, or financial advice.
