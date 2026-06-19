# Consume artifact quality from Python

This tutorial shows how a downstream Python tool can validate and summarize generated artifacts without calling exchange APIs.

The repository includes deterministic synthetic artifacts under `examples/sample_artifacts`. They contain no live market claims and are safe for offline inspection.

## Install for local development

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

## Run the consumer example

```bash
python examples/inspect_quality.py --artifact-root examples/sample_artifacts
```

The command emits a compact JSON object containing:

- validation status and errors;
- artifact mode;
- assets checked;
- overall quality score and grade;
- per-asset score, grade, and timeframes; and
- explicit usage boundaries.

The checked-in fixture currently validates as a two-asset universe with no validation errors. CI tests this contract so missing files or incompatible sample changes fail visibly.

## Use the library API directly

```python
from crypto_composite.artifact_quality import score_artifact_root
from crypto_composite.artifact_validator import validate_artifact_root

artifact_root = "examples/sample_artifacts"
validation = validate_artifact_root(artifact_root)
quality = score_artifact_root(artifact_root)

print(validation["status"])
print(quality["quality_score"], quality["quality_grade"])
```

Call `validate_artifact_root` before consuming fields. Treat `ERROR` as a stop condition and inspect `errors`. Treat `WARN` as a prompt to inspect `warnings` and per-asset details before using an artifact downstream.

## Inspect newly generated artifacts

After running `crypto-composite universe`, point the same example at the selected output directory:

```bash
python examples/inspect_quality.py --artifact-root artifacts-universe
```

Artifact quality scores describe data completeness, coverage, status, and dispersion checks. They are not predictions, rankings, trade recommendations, execution instructions, or profitability estimates.

## Share a downstream use case

When reporting a real integration, include the package version, artifact type, validation status, and concrete workflow. Do not include exchange credentials, private account data, or claims that cannot be verified from public artifacts.

Use the [GitHub issue chooser](https://github.com/thanhlq8-max/crypto-composite-market-data/issues/new/choose) and select **Downstream use case** for reproducible feedback. The form requests a public reference or permission to quote, package version, concrete workflow, artifact or feature used, and observed value or limitation.
