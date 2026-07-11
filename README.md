# crypto-composite-market-data

[![CI](https://github.com/thanhlq8-max/crypto-composite-market-data/actions/workflows/ci.yml/badge.svg)](https://github.com/thanhlq8-max/crypto-composite-market-data/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/crypto-composite-market-data.svg)](https://pypi.org/project/crypto-composite-market-data/)
[![Python](https://img.shields.io/pypi/pyversions/crypto-composite-market-data.svg)](https://pypi.org/project/crypto-composite-market-data/)
[![License](https://img.shields.io/github/license/thanhlq8-max/crypto-composite-market-data.svg)](LICENSE)

Public multi-exchange crypto market-data composite toolkit.

`crypto-composite-market-data` builds reproducible JSON artifacts from public Binance, OKX, Bybit and optional Coinbase Exchange / Kraken spot endpoints. It focuses on market-data normalization, timestamp-aligned OHLCV composition, composite orderbook ladder buckets, multi-symbol universe runs, local artifact inspection, static research reports, and data-quality reporting.

![Read-only artifact dashboard showing synthetic BTC-USDT and ETH-USDT data-quality coverage](https://raw.githubusercontent.com/thanhlq8-max/crypto-composite-market-data/main/docs/assets/dashboard-overview.png)

The dashboard screenshot uses the checked-in synthetic sample artifacts; it does not show live market data or trading signals.

> Note: PyPI/Shields badges can take a few minutes to refresh after a new release.

## Live synthetic demo

A GitHub Pages demo built from checked-in synthetic sample artifacts is available at:

[https://thanhlq8-max.github.io/crypto-composite-market-data/](https://thanhlq8-max.github.io/crypto-composite-market-data/)

The demo opens on a static research dataset report with a companion JSON summary. The dashboard view can still be shared with `asset`, `timeframe`, and `market` query parameters, for example `dashboard.html?asset=BTC-USDT&timeframe=15m&market=spot_usdt`. It does not call live exchange APIs, use private account APIs, rank assets, generate predictions, place orders, or provide financial advice.

## Why this exists

Public crypto market data is fragmented. A single exchange can be stale, unavailable, noisy, rate-limited, or structurally different from the broader venue set.

This project helps developers and researchers answer practical data-quality questions before using market data downstream:

- Which venues returned usable data?
- Is composite OHLCV coverage complete or partial?
- Are prices dispersed across venues?
- Is orderbook depth concentrated in one venue?
- Which assets in a universe have enough public data to inspect?
- Which JSON artifacts were generated and where are they?

See [Why composite public market data](docs/WHY_COMPOSITE_MARKET_DATA.md) for the exact coverage, dispersion, and public orderbook concentration semantics.

## Who it is for

- Data engineers building repeatable public crypto data pipelines.
- Quant researchers who need auditable input artifacts before analysis.
- Dashboard builders who want stable JSON files instead of exchange-specific payloads.
- Open-source contributors who want a small, testable market-data infrastructure project.

## What it does

- Fetches public OHLCV, recent trades, orderbook snapshots, funding and open-interest data.
- Supports optional Coinbase Exchange and Kraken public spot data without private account or order APIs.
- Normalizes records into stable Python dataclasses.
- Builds timestamp-aligned composite OHLCV by market type.
- Builds public composite orderbook ladder buckets near a reference price.
- Reports venue coverage, price dispersion and composite status.
- Runs explicit multi-symbol universes and writes per-asset artifact folders.
- Serves a read-only local artifact dashboard API.
- Writes static research dataset reports and companion summary JSON.
- Exposes an adapted LFX-2 v8.1-D contract for MM Mission / TRADER Mode / NEXT Scenario / DID / DOING / KEY Zones / INV-Release / Confidence-Risk output.
- Adds `lfx_zone_review` objects to observed zones so practical public-depth ranges carry LFX-style role, review value, density-reference context, and refresh checks.
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

From PyPI:

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

## Offline sample report

From a source clone, inspect the checked-in sample artifacts without calling live exchange APIs:

```bash
crypto-composite sample-report
```

This writes:

```text
sample-report/artifact_report.html
sample-report/dashboard.html
sample-report/research_report.html
sample-report/research_summary.json
```

See [docs/SAMPLE_REPORT.md](docs/SAMPLE_REPORT.md).

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
|-- BTC-USDT/
|   |-- composite_ohlcv_15m.json
|   |-- composite_orderbook_ladder_15m.json
|   |-- data_quality.json
|   `-- run_summary.json
|-- ETH-USDT/
|-- SOL-USDT/
`-- universe_summary.json
```

Serve the read-only local artifact API:

```bash
crypto-composite dashboard \
  --artifact-root artifacts-universe \
  --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:18080/
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

## Optional spot-only connectors

Coinbase Exchange and Kraken can be used as additional public spot venues. Use `spot_usdt` only:

```bash
crypto-composite run \
  --asset BTC-USDT \
  --venues binance,okx,bybit,coinbase,kraken \
  --market-types spot_usdt \
  --timeframes 15m \
  --out-dir artifacts-spot
```

See [docs/COINBASE_CONNECTOR.md](docs/COINBASE_CONNECTOR.md) and [docs/KRAKEN_CONNECTOR.md](docs/KRAKEN_CONNECTOR.md).

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

Consume the checked-in fixture through the public validation and quality APIs:

```bash
python examples/inspect_quality.py --artifact-root examples/sample_artifacts
```

See [docs/TUTORIAL_CONSUME_ARTIFACTS.md](docs/TUTORIAL_CONSUME_ARTIFACTS.md) for the offline downstream example.

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

See [docs/ARTIFACT_SCHEMA.md](docs/ARTIFACT_SCHEMA.md).

## Supported scope

| Area | Supported |
|---|---|
| Venues | Binance, OKX, Bybit; Coinbase Exchange and Kraken spot-only |
| Asset format | `BASE-USDT`, for example `BTC-USDT` |
| Market types | `spot_usdt`, `perp_usdt` |
| Timeframes | `1m`, `5m`, `15m`, `1h`, `4h`, `1d` (daily bars anchored to UTC midnight on every venue; Coinbase Exchange has no native `4h` granularity and skips that timeframe) |
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


## Static HTML report

Generate a shareable artifact-quality report:

```bash
crypto-composite report --artifact-root artifacts-universe --out-file report.html
```

The report summarizes quality score, venue coverage, composite OHLCV status, orderbook status, price dispersion, validator warnings/errors, and JSON artifact links. It is an inspection page only; it is not a trading signal, prediction, execution instruction, or financial-advice document.

See [docs/STATIC_REPORT.md](docs/STATIC_REPORT.md).

## Static research dataset report

Generate a shareable research dataset report and companion JSON summary:

```bash
crypto-composite research-report \
  --artifact-root artifacts-universe \
  --out-file research_report.html \
  --summary-file research_summary.json
```

The report focuses on dataset coverage, market microstructure metrics, observed public-depth evidence, source artifacts, and limitations. It is built for reproducible research intake and public demos, not asset ranking, trading signals, predictions, execution, or financial advice.

See [docs/RESEARCH_REPORT.md](docs/RESEARCH_REPORT.md).

## LFX-2 monitor-only alignment

The dashboard snapshot and research summary expose an `lfx_alignment` object that maps the allowed LFX-2 v8.1-D monitor-only contract to public artifact fields: MM Mission, TRADER Mode, NEXT Scenario, DID / Past, DOING / Now, KEY Zones, INV / Release, and Confidence / Risk. Per-market `lfx_mission_control.rows` provide the current artifact-derived readout as object-list data for dashboards, reports, notebooks, and public demos. Each observed zone also includes `lfx_zone_review` for zone role, review value, density-reference text, and counterflow refresh checks.

See [docs/LFX_ALIGNMENT.md](docs/LFX_ALIGNMENT.md).

## CSV export

Export composite OHLCV artifacts to a flat CSV file for spreadsheet, DuckDB, pandas, or notebook inspection:

```bash
crypto-composite export-ohlcv-csv \
  --artifact-root artifacts-universe \
  --out-file composite_ohlcv.csv
```

The export writes one row per asset, timeframe, market type, and composite OHLCV bar. It preserves venue contribution metadata in `venue_weights_json` and remains an artifact-inspection output only.

See [docs/CSV_EXPORT.md](docs/CSV_EXPORT.md).

## Parquet export

The same flat rows are available as a typed Parquet file. Parquet support is an optional extra so the base install keeps its `requests`-only footprint:

```bash
pip install "crypto-composite-market-data[parquet]"

crypto-composite export-ohlcv-parquet \
  --artifact-root artifacts-universe \
  --out-file composite_ohlcv.parquet
```

Columns match the CSV export exactly (`timestamp_ms`/`venue_count` as int64, price and quality fields as float64, the rest as strings).

## Local dashboard API

Serve a read-only local artifact API:

```bash
crypto-composite dashboard --artifact-root artifacts-universe --host 127.0.0.1 --port 18080
```

Endpoints:

```text
/
/api/health
/api/artifacts
/api/dashboard-snapshot
/api/artifact?path=<relative-json-path>
```

Dashboard V3 adds a practical monitoring brief, an eight-row LFX mission-control table, zone-level LFX review roles, a copyable current-view brief, a complete copyable view packet, a copyable nearest zone checklist, copyable observed zone notes, a copyable observed-zones table, a how-to-read observed-zone guide, a multi-timeframe zone map with copyable MTF text for the configured M5/M15/H1 profile, shareable asset/timeframe/market view links, exact zone distance and reference location, composite price and public-depth charts, evidence-grade zones, an observed-zone readout for the nearest bid/ask concentration ranges, and spot/perpetual dislocation context. All observations are derived from generated public-data artifacts and remain non-predictive.

Export the same dashboard as static HTML for GitHub Pages or offline sharing:

```bash
crypto-composite dashboard-export \
  --artifact-root artifacts-universe \
  --out-file site/index.html \
  --artifact-base-url artifacts
```

Write an explicit dashboard profile when an operating view has a locked primary timeframe and refresh cadence:

```bash
crypto-composite dashboard-profile \
  --artifact-root artifacts-universe \
  --primary-timeframe 15m \
  --timeframes 5m,15m,1h \
  --refresh-seconds 60
```

Run a local explicit-universe refresh loop and rewrite a static dashboard on the locked cadence. All material inputs are required; the command does not infer assets, venues, market types, row limits, or depth:

```bash
crypto-composite dashboard-refresh \
  --assets BTC-USDT,ETH-USDT,SOL-USDT \
  --venues binance,okx,bybit \
  --market-types spot_usdt,perp_usdt \
  --timeframes 5m,15m,1h \
  --primary-timeframe 15m \
  --refresh-seconds 60 \
  --limit 120 \
  --depth 100 \
  --bucket-size REVIEWED_BUCKET_SIZE \
  --out-dir artifacts-live \
  --dashboard-file artifacts-live/dashboard.html \
  --artifact-base-url .
```

GitHub Pages remains the synthetic sample demo path. A 60-second live refresh should run from a local machine or external runner that explicitly supplies the command inputs above, including a reviewed price bucket size for the selected assets.

See [docs/DASHBOARD_API.md](docs/DASHBOARD_API.md).

## Community and contribution

Useful first contributions:

- Add a new public exchange connector.
- Improve mocked connector parser coverage.
- Add CSV or DuckDB artifact export.

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), the GitHub issue templates, and [docs/GOOD_FIRST_ISSUES.md](docs/GOOD_FIRST_ISSUES.md).

External users can select **Downstream use case** in the [GitHub issue chooser](https://github.com/thanhlq8-max/crypto-composite-market-data/issues/new/choose) to report a verifiable integration without making trading-performance claims.

## Limitations

Public exchange APIs can rate-limit, return incomplete data, or temporarily fail.

The orderbook ladder is a public snapshot bucket proxy; it is not a private, full-depth, consolidated matching-engine book.

This project is data infrastructure. Any downstream research or visualization must preserve the no-signal, no-execution, no-financial-advice boundary unless explicitly implemented in a separate project with its own validation and legal review.

## Packaging

See [docs/PACKAGING.md](docs/PACKAGING.md) for TestPyPI/PyPI release preparation.

## Development roadmap

See:

- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/USEFUL_OUTPUTS.md](docs/USEFUL_OUTPUTS.md)
- [docs/DASHBOARD_PLAN.md](docs/DASHBOARD_PLAN.md)
- [docs/DASHBOARD_API.md](docs/DASHBOARD_API.md)
- [docs/STATIC_REPORT.md](docs/STATIC_REPORT.md)
- [docs/CSV_EXPORT.md](docs/CSV_EXPORT.md)
- [docs/COINBASE_CONNECTOR.md](docs/COINBASE_CONNECTOR.md)
- [docs/KRAKEN_CONNECTOR.md](docs/KRAKEN_CONNECTOR.md)
- [docs/SAMPLE_REPORT.md](docs/SAMPLE_REPORT.md)
- [docs/TUTORIAL_CONSUME_ARTIFACTS.md](docs/TUTORIAL_CONSUME_ARTIFACTS.md)
- [docs/WHY_COMPOSITE_MARKET_DATA.md](docs/WHY_COMPOSITE_MARKET_DATA.md)
- [docs/GITHUB_PAGES_DEMO.md](docs/GITHUB_PAGES_DEMO.md)
- [docs/PACKAGING.md](docs/PACKAGING.md)
- [docs/COMMUNITY_GROWTH.md](docs/COMMUNITY_GROWTH.md)
- [docs/ADOPTION_PLAYBOOK.md](docs/ADOPTION_PLAYBOOK.md)
- [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)

## Artifact quality scoring

After generating artifacts, compute a compact quality score:

```bash
crypto-composite score-artifacts --artifact-root artifacts-universe --write
```

This writes `quality_score.json` with a reproducible A-F grade based on venue coverage, composite OHLCV coverage, price dispersion, orderbook coverage and existing data-quality status. The score is for artifact inspection only; it is not a trading signal or prediction score.

See [docs/ARTIFACT_QUALITY_SCORE.md](docs/ARTIFACT_QUALITY_SCORE.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).


## Operational briefing report

The static report includes an LFX-style monitor-only artifact readout derived from composite OHLCV and public ladder artifacts:

- MM Mission: the current public-artifact review job.
- TRADER Mode: the quality-gated review posture.
- NEXT Scenario: conditional evidence to check after refresh.
- DID / Past: recent composite OHLCV behavior.
- DOING / Now: latest public book and nearest concentration context.
- KEY Zones: practical public-depth ranges.
- INV / Release: public depth imbalance proxy and reference context.
- Confidence / Risk: coverage, evidence mix, and single-snapshot caveats.

This is public-data context only and does not provide execution guidance, position sizing, prediction, or financial advice.
