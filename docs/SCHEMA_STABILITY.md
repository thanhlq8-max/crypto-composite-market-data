# Artifact schema stability

This project ships a machine-readable contract for its JSON artifacts as
committed JSON Schema files, and a stability policy for how that contract may
change. The prose contract is in [`ARTIFACT_SCHEMA.md`](ARTIFACT_SCHEMA.md); the
schemas are the authoritative, testable form of it.

## Committed schemas

Draft 2020-12 JSON Schema files live in the packaged resource directory
`src/crypto_composite/artifact_schemas/` (so a wheel install can validate too):

| Schema | Covers |
|---|---|
| `run_summary.schema.json` | `run_summary.json` |
| `data_quality.schema.json` | `data_quality.json` (timeframe → report map) |
| `composite_ohlcv.schema.json` | `composite_ohlcv_<timeframe>.json` |
| `composite_orderbook_ladder.schema.json` | `composite_orderbook_ladder_<timeframe>.json` (market_type → ladder) |
| `universe_summary.schema.json` | `universe_summary.json` |

The combined `composite_ohlcv.json` / `composite_orderbook_ladder.json` files nest
these same objects under timeframe keys and are intentionally left unschematized
for now. `zone_lifecycle*.json` (stream extra) is documented in prose only.

## Validate against the contract

Schema validation uses the optional `jsonschema` dependency, so the base install
stays `requests`-only. Enable it with the `[schema]` extra:

```bash
pip install "crypto-composite-market-data[schema]"
crypto-composite validate-artifacts --artifact-root artifacts-universe --json-schema
```

The committed sample artifacts under `examples/sample_artifacts/` are validated
against these schemas in CI, so the contract cannot silently drift.

## Stability policy

The stable release line (1.0 onward) treats artifact fields as **additive-only**:

- **Required fields are never renamed or removed.** A field listed in a schema's
  `required` array is part of the contract; consumers may depend on it.
- **New fields are additive.** Every schema sets `additionalProperties: true` on
  artifact bodies, and consumers **must** tolerate unknown fields. Adding a field
  is a minor, non-breaking change.
- **Types of existing fields do not change** (a `number` stays a `number`).
- **File names and directory layout** in `ARTIFACT_SCHEMA.md` are part of the
  contract; a consumer must not have to guess new filenames.

A change that would break any of the above is a **breaking contract change**. It
requires, in order: release notes calling it out, an explicit artifact
`schema_version` strategy (artifacts do not carry one today), and a major-version
bump. Until then, no such change ships.

## Effective from 1.0

The additive-only guarantee is in effect as of v1.0.0. On the schematized
artifacts, required fields will not be renamed or removed and existing field
types will not change without a major-version bump and the process above. Adding
a new *required* field to an existing artifact is a breaking change under this
policy; adding a new *optional* field is not. Artifacts that are not yet
schematized (the combined timeframe-nested files and `zone_lifecycle*.json`) are
still described by prose in `ARTIFACT_SCHEMA.md` and may gain schemas additively.
