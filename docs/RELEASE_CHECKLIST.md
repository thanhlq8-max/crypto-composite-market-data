# Release checklist

Use this checklist before every PyPI release.

## Pre-release

- [ ] `pyproject.toml` version is bumped.
- [ ] `src/crypto_composite/__init__.py` version matches `pyproject.toml`.
- [ ] `RELEASE_NOTES_vX.Y.Z.md` exists.
- [ ] No local patch files are tracked.
- [ ] `git status` is clean before tagging.
- [ ] CI passes on Python 3.11, 3.12 and 3.13.

## Local validation

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m compileall src
python -m pytest -q
python -m build
```

## Publishing order

1. Push release commit to `main`.
2. Run `Publish to TestPyPI`.
3. Install from TestPyPI in a clean environment.
4. Run `crypto-composite --help`.
5. Run a small `universe` smoke test.
6. Run `Publish to PyPI`.
7. Verify `pip install crypto-composite-market-data` from PyPI.
8. Create a GitHub tag and release.

## Windows validation without activating venv

```powershell
D:\ccmd-pypi-verify\Scripts\python.exe -m pip install crypto-composite-market-data
D:\ccmd-pypi-verify\Scripts\python.exe -c "import crypto_composite; print(crypto_composite.__version__)"
D:\ccmd-pypi-verify\Scripts\crypto-composite.exe --help
```
