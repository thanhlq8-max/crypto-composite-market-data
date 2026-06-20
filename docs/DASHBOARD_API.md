# Dashboard UI and API

The local dashboard is a read-only artifact browser built on Python's standard-library HTTP server. It serves a static frontend and JSON endpoints from the same local origin.

## Start

```bash
crypto-composite dashboard --artifact-root artifacts-universe --host 127.0.0.1 --port 18080
```

Open `http://127.0.0.1:18080/` for the frontend.

## Screenshot

![Read-only dashboard rendered from the checked-in synthetic sample artifacts](assets/dashboard-overview.png)

This screenshot is rendered from `examples/sample_artifacts`. The values are deterministic fixture data, not live market data.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `/` | Static artifact health and data-quality frontend |
| `/api/health` | Service health check |
| `/api/artifacts` | List JSON artifact paths and byte sizes |
| `/api/artifact?path=<relative-json-path>` | Read one JSON artifact by relative path |

## Health contract

`/api/health` returns the service identity and current status:

```json
{
  "service": "crypto-composite-dashboard",
  "status": "OK"
}
```

## Artifact index contract

`/api/artifacts` returns an object. Its `artifacts` field is an object list, not a string list:

```json
{
  "artifact_count": 2,
  "artifacts": [
    {
      "path": "BTC-USDT/data_quality.json",
      "size_bytes": 481
    },
    {
      "path": "universe_summary.json",
      "size_bytes": 902
    }
  ],
  "well_known": {
    "universe_summary.json": true
  }
}
```

Each artifact entry has exactly these public index fields:

- `path`: forward-slash relative path under the selected artifact root;
- `size_bytes`: current file size in bytes.

The object-list contract replaces the earlier string-list response. Consumers must read `entry.path` instead of treating each entry as a string.

## Frontend panels

The frontend reads the API at runtime and displays:

- service health;
- artifact count and total size;
- well-known root-file coverage;
- timeframe status, overall quality, and venue coverage from `data_quality.json` files;
- artifact paths and sizes; and
- a read-only JSON inspector.

Dynamic artifact values are inserted as text, not executable HTML.

## Boundary

The dashboard does not produce trading signals, asset rankings, entry or exit instructions, order execution, position sizing, predictions, or financial advice. It only exposes generated data artifacts and data-quality context.

## Troubleshooting

On Windows, a local port can be unavailable because it is already bound, excluded, or blocked by local security policy. If dashboard startup returns `DASHBOARD_BIND_FAILED` or `WinError 10013`, retry with a different local port:

```bash
crypto-composite dashboard --artifact-root artifacts-universe --host 127.0.0.1 --port 18081
```

Do not stop an unrelated process. Changing the dashboard port does not change generated market-data artifacts.
