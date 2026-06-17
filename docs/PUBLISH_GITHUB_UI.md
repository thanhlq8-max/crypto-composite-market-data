# Publish to GitHub by UI

Use this checklist when creating the repository from the GitHub **Create a new repository** screen.

## 1. Create the empty GitHub repository

On the GitHub page:

| Field | Value |
|---|---|
| Owner | `thanhlq8-max` |
| Repository name | `crypto-composite-market-data` |
| Description | `Public crypto market-data composite toolkit for multi-exchange OHLCV and orderbook artifacts.` |
| Visibility | `Public` |
| Add README | `Off` |
| Add .gitignore | `No .gitignore` |
| Add license | `No license` |

Why README / .gitignore / license should remain off:

- This local repository already includes `README.md`.
- This local repository already includes `.gitignore`.
- This local repository already includes `LICENSE` using Apache-2.0.
- Letting GitHub generate those files can create a different first commit and produce push conflicts.

Click **Create repository**.

## 2. Push the prepared local repository

From the local repository folder:

```powershell
git init
git branch -M main
git add .
git commit -m "Initial public release"
git remote add origin https://github.com/thanhlq8-max/crypto-composite-market-data.git
git push -u origin main
```

## 3. Verify CI

Open the GitHub repository and go to:

```text
Actions
```

The workflow `.github/workflows/ci.yml` should run on Python 3.11 and 3.12.

## 4. Configure About section

On the repository page, edit the **About** block.

Description:

```text
Public crypto market-data composite toolkit for multi-exchange OHLCV and orderbook artifacts.
```

Topics:

```text
python, crypto, market-data, ohlcv, orderbook, binance, okx, bybit, data-engineering, quant-research, open-source
```

Do not use topics such as:

```text
trading-bot, buy-sell-signal, market-maker-detector, smart-money
```

## 5. Create the first release

After CI passes:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Then in GitHub:

```text
Releases -> Draft a new release -> Choose tag v0.1.0
```

Release title:

```text
v0.1.0 — Initial public market-data composite toolkit
```

Release notes:

```markdown
Initial public release.

Includes:
- Binance / OKX / Bybit public REST connectors
- Composite OHLCV artifact builder
- Composite orderbook ladder artifact builder
- Data-quality reporting
- CLI pipeline
- Tests and CI

Non-goals:
- No trading signals
- No order execution
- No financial advice
```
