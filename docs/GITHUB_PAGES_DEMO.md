# GitHub Pages synthetic artifact demo

The repository contains a manual GitHub Pages workflow that builds the static artifact report from checked-in synthetic fixtures.

The workflow does not call exchange APIs, does not use live market data, and does not run automatically on push.

## Workflow

```text
.github/workflows/deploy-pages.yml
```

It performs these steps:

1. installs the package from the checked-out source;
2. copies `examples/sample_artifacts` into the Pages staging directory;
3. validates and scores the copied artifact tree;
4. generates `_site/index.html` with the static report command;
5. uploads one Pages artifact; and
6. deploys it to the protected `github-pages` environment.

The deployed report links to the copied JSON files under `_site/artifacts`, so the demo remains self-contained.

## Enable and deploy

Repository admin access is required.

1. Open **Settings > Pages**.
2. Under **Build and deployment**, select **GitHub Actions** as the source.
3. Open **Actions > Deploy synthetic artifact report to GitHub Pages**.
4. Select **Run workflow** on the reviewed branch.
5. Wait for both `build-static-demo` and `deploy-static-demo` to pass.
6. Open the URL reported by the `github-pages` deployment environment.

Do not describe the expected Pages URL as live until the deployment has passed and the page has been opened successfully.

## Local reproduction

From the repository root on a POSIX-compatible shell:

```bash
python -m pip install -e .
mkdir .pages-preview
cp -R examples/sample_artifacts .pages-preview/artifacts
crypto-composite validate-artifacts --artifact-root .pages-preview/artifacts
crypto-composite score-artifacts --artifact-root .pages-preview/artifacts --write
crypto-composite report \
  --artifact-root .pages-preview/artifacts \
  --out-file .pages-preview/index.html
```

Verify that:

- validation exits successfully;
- `index.html` identifies the report as artifact inspection only;
- BTC-USDT and ETH-USDT are present;
- JSON artifact links resolve inside `.pages-preview/artifacts`; and
- no page claims live market conditions, trading signals, rankings, or profitability.

Use a clean checkout or remove any previous `.pages-preview` directory before running the commands. The directory is ignored generated output and must not be committed.

## Boundary

The Pages site is a reproducible synthetic artifact demo. It is not evidence of external adoption by itself and must not be recorded as an external user, downstream project, or independent publication.
