## Problem

Describe the issue or user need this pull request addresses.

Closes #

## Scope

List the files or modules intentionally changed and any explicitly excluded work.

## Changes

- Describe each user-visible change.

## Validation

Record the commands run and their results:

```text
python -m compileall src
python -m pytest -q
python -m build
```

## Checklist

- [ ] The change is narrow and linked to a documented issue or requirement.
- [ ] Tests or documentation cover the observable behavior.
- [ ] Connector tests use mocked responses; CI does not require live exchange calls.
- [ ] No secrets, private artifacts, build outputs, or local environment files are included.
- [ ] No trading signals, order execution, private account APIs, position sizing, profitability claims, or financial advice are introduced.
- [ ] User-facing artifact or CLI compatibility changes are documented.
