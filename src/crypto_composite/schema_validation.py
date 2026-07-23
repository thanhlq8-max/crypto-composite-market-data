"""Validate generated artifacts against the committed JSON Schema contract.

The schemas live in the packaged ``crypto_composite.artifact_schemas`` resource
directory, so a wheel install can validate too. ``jsonschema`` is an optional
dependency (the ``[schema]`` extra); the base install stays ``requests``-only, so
it is imported lazily and a clear error explains how to enable strict validation.

Only per-timeframe and single-object artifacts are covered here. The combined
``composite_ohlcv.json`` / ``composite_orderbook_ladder.json`` files nest the same
objects under timeframe keys and are intentionally left unschematized for now
(``schema_name_for_filename`` returns ``None`` for them).
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

_SCHEMA_PACKAGE = "crypto_composite.artifact_schemas"

# Schema name -> committed resource filename.
SCHEMA_FILES = {
    "run_summary": "run_summary.schema.json",
    "data_quality": "data_quality.schema.json",
    "composite_ohlcv": "composite_ohlcv.schema.json",
    "composite_orderbook_ladder": "composite_orderbook_ladder.schema.json",
    "universe_summary": "universe_summary.schema.json",
}

# Artifacts whose filename equals the schema name.
_EXACT_NAME_SCHEMAS = frozenset({"run_summary", "data_quality", "universe_summary"})
# Artifacts written per timeframe as ``<name>_<timeframe>.json``.
_PER_TIMEFRAME_SCHEMAS = frozenset({"composite_ohlcv", "composite_orderbook_ladder"})


class SchemaValidationUnavailable(RuntimeError):
    """Raised when the optional ``jsonschema`` dependency is not installed."""


def available_schemas() -> tuple[str, ...]:
    return tuple(SCHEMA_FILES)


def load_schema(name: str) -> dict[str, Any]:
    try:
        resource = SCHEMA_FILES[name]
    except KeyError:
        raise KeyError(f"unknown schema {name!r}; known: {', '.join(SCHEMA_FILES)}") from None
    text = (resources.files(_SCHEMA_PACKAGE) / resource).read_text(encoding="utf-8")
    return json.loads(text)


def schema_name_for_filename(filename: str) -> str | None:
    """Map an artifact filename to a schema name, or ``None`` if unschematized.

    ``run_summary.json`` -> ``run_summary``; ``composite_ohlcv_15m.json`` ->
    ``composite_ohlcv``; the combined ``composite_ohlcv.json`` -> ``None``.
    """
    stem = filename[:-5] if filename.endswith(".json") else filename
    if stem in _EXACT_NAME_SCHEMAS:
        return stem
    for base in _PER_TIMEFRAME_SCHEMAS:
        if stem.startswith(base + "_"):
            return base
    return None


def _require_jsonschema():
    try:
        import jsonschema
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised via the extra
        raise SchemaValidationUnavailable(
            "JSON Schema validation needs the optional 'jsonschema' dependency; "
            "install it with: pip install crypto-composite-market-data[schema]"
        ) from exc
    return jsonschema


def validate(name: str, data: Any) -> list[str]:
    """Return sorted human-readable schema violations for ``data`` (empty = valid)."""
    jsonschema = _require_jsonschema()
    schema = load_schema(name)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    return [
        f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in errors
    ]


def validate_artifact_root(root: str | Path) -> dict[str, Any]:
    """Validate every schematized JSON file under ``root`` against the contract.

    Raises :class:`SchemaValidationUnavailable` if ``jsonschema`` is not installed.
    """
    _require_jsonschema()
    root_path = Path(root)
    files: dict[str, dict[str, Any]] = {}
    ok = True
    for path in sorted(root_path.rglob("*.json")):
        name = schema_name_for_filename(path.name)
        if name is None:
            continue
        rel = str(path.relative_to(root_path))
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            files[rel] = {"schema": name, "errors": [f"unreadable: {exc}"]}
            ok = False
            continue
        errors = validate(name, data)
        files[rel] = {"schema": name, "errors": errors}
        if errors:
            ok = False
    return {"status": "OK" if ok else "ERROR", "checked": len(files), "files": files}
