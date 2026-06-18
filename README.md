# crypto-composite-market-data

Public multi-exchange crypto market-data composite toolkit.

This repository builds reproducible JSON artifacts from public Binance, OKX and Bybit endpoints. It focuses on market-data normalization, timestamp-aligned OHLCV composition, composite orderbook ladder buckets and data-quality reporting.

## What it does

- Fetches public OHLCV, recent trades, orderbook snapshots, funding and open-interest data.
- Normalizes records into stable Python dataclasses.
- Builds timestamp-aligned composite OHLCV by market type.
- Builds public composite orderbook ladder buckets near a reference price.
- Reports venue coverage, price dispersion and composite status.
- Writes reproducible JSON artifacts for research, dashboards and downstream analytics.

## What it does not do

- No trading signals.
- No order execution.
- No private exchange account APIs.
- No position sizing.
- No financial advice.
- No private orderflow or market-maker intent claim.
- No profitability or statistical-edge claim.

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

For development:

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Quick start

```bash
crypto-composite run \
  --asset BTC-USDT \
  --venues binance,okx,bybit \
  --market-types spot_usdt,perp_usdt \
  --timeframes 15m \
  --limit 300 \
  --depth 100 \
  --out-dir artifacts
```

Equivalent module form:

```bash
python -m crypto_composite.cli run \
  --asset BTC-USDT \
  --venues binance,okx,bybit \
  --market-types spot_usdt,perp_usdt \
  --timeframes 15m \
  --out-dir artifacts
```

## Output artifacts

For each timeframe:

```text
artifacts/raw_scan_15m.json
artifacts/composite_ohlcv_15m.json
artifacts/composite_orderbook_ladder_15m.json
```

Combined outputs:

```text
artifacts/composite_ohlcv.json
artifacts/composite_orderbook_ladder.json
artifacts/data_quality.json
artifacts/run_summary.json
```

## Supported scope

| Area | Supported |
|---|---|
| Venues | Binance, OKX, Bybit |
| Asset format | `BASE-USDT`, for example `BTC-USDT` |
| Market types | `spot_usdt`, `perp_usdt` |
| Timeframes | `1m`, `5m`, `15m`, `1h` |
| Data access | Public REST endpoints only |

## Composite OHLCV model

For each timestamp and market type, the engine computes:

- weighted open;
- high / low envelope;
- median close;
- quote-volume-weighted close;
- total base and quote volume;
- venue weights;
- venue coverage;
- price dispersion percentage;
- data-quality score.

Status labels:

```text
COMPOSITE_DATA_OK
COMPOSITE_DATA_PARTIAL
COMPOSITE_DATA_WEAK
```

## Composite orderbook ladder model

The ladder engine merges public orderbook snapshots into near-book price buckets. For each bucket, it computes:

- quote depth;
- contributing venue count;
- venue depth map;
- HHI concentration;
- persistence proxy;
- spoof-risk proxy;
- vacuum score.

Status labels:

```text
COMPOSITE_BOOK_OK
COMPOSITE_BOOK_PARTIAL
COMPOSITE_BOOK_WEAK
```

## Limitations

Public exchange APIs can rate-limit, return incomplete data, or temporarily fail. The orderbook ladder is a public snapshot bucket proxy; it is not a private, full-depth, consolidated matching-engine book.

This project is data infrastructure. Any downstream research or visualization must preserve the no-signal, no-execution, no-financial-advice boundary unless explicitly implemented in a separate project with its own validation and legal review.


## Repository publishing

Recommended GitHub repository settings:

- Repository name: `crypto-composite-market-data`
- Visibility: Public
- Add README: Off
- Add .gitignore: No .gitignore
- Add license: No license

The repository already includes `README.md`, `.gitignore` and `LICENSE`. See [docs/PUBLISH_GITHUB_UI.md](docs/PUBLISH_GITHUB_UI.md) for the UI-based publishing checklist.


## Multi-symbol universe mode

Run an explicit asset universe without producing rankings or trading signals:

```bash
crypto-composite universe   --assets BTC-USDT,ETH-USDT,SOL-USDT   --venues binance,okx,bybit   --market-types spot_usdt,perp_usdt   --timeframes 15m,1h   --out-dir artifacts-universe
```

This writes per-asset artifacts plus `universe_summary.json`. See `docs/MULTI_SYMBOL_UNIVERSE.md`.

## Local dashboard API

Serve a read-only local artifact API:

```bash
crypto-composite dashboard --artifact-root artifacts-universe --host 127.0.0.1 --port 18080
```

Endpoints:

```text
/api/health
/api/artifacts
/api/artifact?path=<relative-json-path>
```

See `docs/DASHBOARD_API.md`.

## Packaging

See `docs/PACKAGING.md` for TestPyPI/PyPI release preparation.

## Development roadmap

See:

- `docs/ROADMAP.md`
- `docs/USEFUL_OUTPUTS.md`
- `docs/DASHBOARD_PLAN.md`
- `docs/DASHBOARD_API.md`
- `docs/PACKAGING.md`

## License

Apache License 2.0. See [LICENSE](LICENSE).
