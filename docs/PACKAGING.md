# Packaging and release workflow

This project should publish packages only after CI passes and the repository contains no local patch files, secrets, generated build folders, or private artifacts.

## Current release path

1. Merge or push the release candidate branch.
2. Confirm GitHub Actions `CI` passes.
3. Build locally if desired:

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m compileall src
python -m pytest -q
python -m build
```

4. Create a GitHub release tag:

```bash
git tag v0.3.0
git push origin v0.3.0
```

5. Run the manual `Publish to TestPyPI` workflow from GitHub Actions.
6. Install from TestPyPI in a clean environment and run `crypto-composite --help`.
7. Publish to production PyPI only after the TestPyPI package has been verified.

## Trusted publishing

The included TestPyPI workflow expects GitHub Actions trusted publishing. Configure the package on TestPyPI with:

- Owner: `thanhlq8-max`
- Repository: `crypto-composite-market-data`
- Workflow: `publish-testpypi.yml`
- Environment: `testpypi`

Do not store PyPI passwords or API tokens in the repository.

## Release quality gate

Before a production PyPI release:

- CI passes on Python 3.11, 3.12, and 3.13.
- `python -m build` succeeds.
- `dist/` is not committed.
- No `*.patch` files are committed.
- README and release notes match the package version.
- Examples are illustrative or reproducible without private credentials.
- No live API tests are required for CI.
