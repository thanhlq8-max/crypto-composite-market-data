# Dashboard API

The starter dashboard API is a read-only local artifact browser built on Python stdlib HTTP. It is designed for quick inspection of generated JSON outputs without introducing a frontend stack.

## Start

```bash
crypto-composite dashboard --artifact-root artifacts-universe --host 127.0.0.1 --port 18080
```

## Endpoints

| Endpoint | Purpose |
|---|---|
| `/api/health` | Service health check |
| `/api/artifacts` | List JSON artifacts under the artifact root |
| `/api/artifact?path=<relative-json-path>` | Read one JSON artifact by relative path |

## Boundary

The dashboard API does not produce trading signals, asset rankings, entry/exit instructions, order execution, position sizing, or financial advice. It only exposes generated data artifacts.

## Next dashboard direction

A future frontend can be built on this API with panels for:

- universe health;
- venue coverage;
- composite OHLCV quality;
- orderbook ladder concentration;
- spot/perp divergence context;
- artifact manifest inspection.

## Troubleshooting

On Windows, a local port can be unavailable because it is already bound, excluded, or blocked by local security policy. If dashboard startup returns `DASHBOARD_BIND_FAILED` or `WinError 10013`, retry with a different local port:

```bash
crypto-composite dashboard --artifact-root artifacts-universe --host 127.0.0.1 --port 18081
```

The dashboard is a local read-only API. Changing the port does not change generated market-data artifacts.
