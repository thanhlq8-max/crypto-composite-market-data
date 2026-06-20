# Windows quickstart without PowerShell activation

This guide uses the virtual environment's executables directly. It does not require `Activate.ps1` or an execution-policy change.

## Prerequisite

Install Python 3.11, 3.12, or 3.13 and confirm the selected interpreter:

```powershell
python --version
```

## Install in a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install crypto-composite-market-data
.\.venv\Scripts\crypto-composite.exe --help
```

## Generate a small universe

```powershell
.\.venv\Scripts\crypto-composite.exe universe `
  --assets BTC-USDT,ETH-USDT,SOL-USDT `
  --venues binance,okx,bybit `
  --market-types spot_usdt,perp_usdt `
  --timeframes 15m `
  --limit 100 `
  --out-dir artifacts-universe
```

Validate and score the generated artifacts:

```powershell
.\.venv\Scripts\crypto-composite.exe validate-artifacts --artifact-root artifacts-universe
.\.venv\Scripts\crypto-composite.exe score-artifacts --artifact-root artifacts-universe --write
```

## Inspect artifacts locally

Start the read-only API on an explicit local port:

```powershell
.\.venv\Scripts\crypto-composite.exe dashboard `
  --artifact-root artifacts-universe `
  --host 127.0.0.1 `
  --port 18080
```

Open:

```text
http://127.0.0.1:18080/
http://127.0.0.1:18080/api/health
http://127.0.0.1:18080/api/artifacts
```

Generate a static report instead of starting a server:

```powershell
.\.venv\Scripts\crypto-composite.exe report `
  --artifact-root artifacts-universe `
  --out-file report.html
```

## Port bind errors

If the dashboard reports `DASHBOARD_BIND_FAILED`, do not stop an unrelated process. Choose another unused local port and pass it explicitly, for example:

```powershell
.\.venv\Scripts\crypto-composite.exe dashboard `
  --artifact-root artifacts-universe `
  --host 127.0.0.1 `
  --port 18081
```

Changing the dashboard port does not change generated artifacts.

## Development checkout

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest_cache\basetemp
.\.venv\Scripts\python.exe -m build
```

The project reads public market-data endpoints only. Do not provide exchange credentials, wallet keys, cookies, or private account data.
