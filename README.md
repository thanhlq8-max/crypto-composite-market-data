# crypto-composite-market-data

[![CI](https://github.com/thanhlq8-max/crypto-composite-market-data/actions/workflows/ci.yml/badge.svg)](https://github.com/thanhlq8-max/crypto-composite-market-data/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/crypto-composite-market-data.svg)](https://pypi.org/project/crypto-composite-market-data/)
[![Python](https://img.shields.io/pypi/pyversions/crypto-composite-market-data.svg)](https://pypi.org/project/crypto-composite-market-data/)
[![License](https://img.shields.io/github/license/thanhlq8-max/crypto-composite-market-data.svg)](LICENSE)

Public multi-exchange crypto market-data composite toolkit.

`crypto-composite-market-data` builds reproducible JSON artifacts from public Binance, OKX and Bybit endpoints. It focuses on market-data normalization, timestamp-aligned OHLCV composition, composite orderbook ladder buckets, multi-symbol universe runs, local artifact inspection, and data-quality reporting.

## Why this exists

Public crypto market data is fragmented. A single exchange can be stale, unavailable, noisy, rate-limited, or structurally different from the broader venue set. This project helps developers and researchers answer practical data-quality questions before using market data downstream:

- Which venues returned usable data?
- Is composite OHLCV coverage complete or partial?
- Are prices dispersed across venues?
- Is orderbook depth concentrated in one venue?
- Which assets in a universe have enough public data to inspect?
- Which JSON artifacts were generated and where are they?

## Who it is for

- Data engineers building repeatable public crypto data pipelines.
- Quant researchers who need auditable input artifacts before analysis.
- Dashboard builders who want stable JSON files instead of exchange-specific payloads.
- Open-source contributors who want a small, testable market-data infrastructure project.

## What it does

- Fetches public OHLCV, recent trades, orderbook snapshots, funding and open-interest data.
- Normalizes records into stable Python dataclasses.
- Builds timestamp-aligned composite OHLCV by market type.
- Builds public composite orderbook ladder buckets near a reference price.
- Reports venue coverage, price dispersion and composite status.
- Runs explicit multi-symbol universes and writes per-asset artifact folders.
- Serves a read-only local artifact dashboard API.
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

From PyPI after production release:

```bash
pip install crypto-composite-market-data
```

From TestPyPI for release candidates:

```bash
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  crypto-composite-market-data
```

For local development:

```bash
git clone https://github.com/thanhlq8-max/crypto-composite-market-data.git
cd crypto-composite-market-data
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m pytest -q
```

## 5-minute quickstart

Create a small multi-asset universe:

```bash
crypto-composite universe \
  --assets BTC-USDT,ETH-USDT,SOL-USDT \
  --venues binance,okx,bybit \
  --market-types spot_usdt,perp_usdt \
  --timeframes 15m \
  --limit 100 \
  --out-dir artifacts-universe
```

Inspect the generated files:

```text
artifacts-universe/
├── BTC-USDT/
│   ├── composite_ohlcv_15m.json
│   ├── composite_orderbook_ladder_15m.json
│   ├── data_quality.json
│   └── run_summary.json
├── ETH-USDT/
├── SOL-USDT/
└── universe_summary.json
```

Serve the read-only local artifact API:

```bash
crypto-composite dashboard \
  --artifact-root artifacts-universe \
  --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:18080/api/health
http://127.0.0.1:18080/api/artifacts
```

See [docs/QUICKSTART_5_MIN.md](docs/QUICKSTART_5_MIN.md) for Windows and venv-safe commands.

## Single-asset run

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

## Useful output preview

A `data_quality.json` artifact summarizes whether downstream consumers should trust the generated composite data:

```json
{
  "timeframes": {
    "15m": {
      "ohlcv_status": "COMPOSITE_DATA_OK",
      "book_status": "COMPOSITE_BOOK_OK",
      "ohlcv_coverage": 1.0,
      "book_coverage": 1.0
    }
  }
}
```

A `universe_summary.json` artifact summarizes multi-symbol runs without producing rankings or trading signals:

```json
{
  "asset_count": 3,
  "assets": ["BTC-USDT", "ETH-USDT", "SOL-USDT"],
  "boundaries": [
    "No trading signals, order execution, position sizing, or financial advice."
  ]
}
```

Sample illustrative artifacts are available under [examples/sample_artifacts](examples/sample_artifacts/).

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

Multi-symbol output:

```text
artifacts-universe/<ASSET>/...
artifacts-universe/universe_summary.json
```

See [docs/ARTIFACT_SCHEMA.md](docs/ARTIFACT_SCHEMA.md) and [docs/OUTPUT_ARTIFACTS.md](docs/OUTPUT_ARTIFACTS.md).

## Supported scope

| Area | Supported |
|---|---|
| Venues | Binance, OKX, Bybit |
| Asset format | `BASE-USDT`, for example `BTC-USDT` |
| Market types | `spot_usdt`, `perp_usdt` |
| Timeframes | `1m`, `5m`, `15m`, `1h` |
| Data access | Public REST endpoints only |
| Python | 3.11, 3.12, 3.13 |

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

See [docs/DASHBOARD_API.md](docs/DASHBOARD_API.md).

## Community and contribution

Useful first contributions:

- Add a new public exchange connector.
- Improve mocked connector parser coverage.
- Add CSV or DuckDB artifact export.
- Improve Windows setup documentation.
- Build a small static frontend on top of the read-only dashboard API.
- Add schema validation for output artifacts.

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and the GitHub issue templates.

## Limitations

Public exchange APIs can rate-limit, return incomplete data, or temporarily fail. The orderbook ladder is a public snapshot bucket proxy; it is not a private, full-depth, consolidated matching-engine book.

This project is data infrastructure. Any downstream research or visualization must preserve the no-signal, no-execution, no-financial-advice boundary unless explicitly implemented in a separate project with its own validation and legal review.

## Packaging

See [docs/PACKAGING.md](docs/PACKAGING.md) for TestPyPI/PyPI release preparation.

## Development roadmap

See:

- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/USEFUL_OUTPUTS.md](docs/USEFUL_OUTPUTS.md)
- [docs/DASHBOARD_PLAN.md](docs/DASHBOARD_PLAN.md)
- [docs/DASHBOARD_API.md](docs/DASHBOARD_API.md)
- [docs/PACKAGING.md](docs/PACKAGING.md)
- [docs/COMMUNITY_GROWTH.md](docs/COMMUNITY_GROWTH.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).
