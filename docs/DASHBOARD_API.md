# Dashboard API

The starter dashboard API is a read-only local artifact browser built on Python stdlib HTTP. It is designed for quick inspection of generated JSON outputs without introducing a frontend stack.

## Start

```bash
crypto-composite dashboard --artifact-root artifacts-universe --host 127.0.0.1 --port 8765
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
