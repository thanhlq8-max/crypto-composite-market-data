from __future__ import annotations

from pathlib import Path
from typing import Any

from crypto_composite.artifact_csv import CSV_COLUMNS, _asset_rows, _universe_rows
from crypto_composite.artifact_validator import validate_artifact_root

NO_SIGNAL_BOUNDARY = (
    "Composite OHLCV Parquet export only; no trading signal, execution instruction, or financial advice."
)

# Same flat row shape as the CSV export so downstream consumers can switch
# formats without remapping columns.
PARQUET_COLUMNS = CSV_COLUMNS

_INT_COLUMNS = {"timestamp_ms", "venue_count"}
_FLOAT_COLUMNS = {
    "open",
    "high",
    "low",
    "close",
    "median_close",
    "vwap_close",
    "volume_base_total",
    "volume_quote_total",
    "coverage",
    "price_dispersion_pct",
    "data_quality",
}


class ParquetDependencyError(RuntimeError):
    """Raised when the optional pyarrow dependency is not installed."""


def _load_pyarrow():
    try:
        import pyarrow  # noqa: PLC0415 - optional dependency, imported lazily
        import pyarrow.parquet  # noqa: F401, PLC0415
    except ImportError as exc:
        raise ParquetDependencyError(
            "PARQUET_DEPENDENCY_MISSING: pyarrow is required for Parquet export; "
            "install with: pip install crypto-composite-market-data[parquet]"
        ) from exc
    return pyarrow


def _column_values(rows: list[dict[str, Any]], column: str) -> list[Any]:
    values: list[Any] = []
    for row in rows:
        value = row.get(column, "")
        if value == "" or value is None:
            values.append(None)
        elif column in _INT_COLUMNS:
            values.append(int(value))
        elif column in _FLOAT_COLUMNS:
            values.append(float(value))
        else:
            values.append(str(value))
    return values


def _rows_to_table(rows: list[dict[str, Any]], pyarrow_module) -> Any:
    pa = pyarrow_module
    fields = []
    arrays = []
    for column in PARQUET_COLUMNS:
        if column in _INT_COLUMNS:
            dtype = pa.int64()
        elif column in _FLOAT_COLUMNS:
            dtype = pa.float64()
        else:
            dtype = pa.string()
        fields.append(pa.field(column, dtype))
        arrays.append(pa.array(_column_values(rows, column), type=dtype))
    return pa.Table.from_arrays(arrays, schema=pa.schema(fields))


def write_composite_ohlcv_parquet(artifact_root: str | Path, out_file: str | Path) -> dict[str, Any]:
    """Export generated composite OHLCV artifacts to a flat Parquet file.

    Mirrors the CSV export row-for-row and column-for-column with typed
    columns. The export preserves artifact inspection boundaries. It does not
    rank assets, generate predictions, produce trading signals, or create
    execution advice.
    """
    pa = _load_pyarrow()
    import pyarrow.parquet as pq  # noqa: PLC0415 - optional dependency, imported lazily

    root = Path(artifact_root)
    parquet_path = Path(out_file)
    validation = validate_artifact_root(root)
    result: dict[str, Any] = {
        "status": "OK",
        "artifact_root": str(root),
        "parquet_path": str(parquet_path),
        "row_count": 0,
        "assets_checked": 0,
        "errors": [],
        "warnings": [],
        "validation": validation,
        "boundaries": [NO_SIGNAL_BOUNDARY],
    }

    if validation.get("status") == "ERROR":
        result["status"] = "ERROR"
        result["errors"] = list(validation.get("errors", []))
        result["warnings"] = list(validation.get("warnings", []))
        return result

    if validation.get("mode") == "universe":
        rows, assets_checked = _universe_rows(root)
    else:
        rows = _asset_rows(root)
        assets_checked = 1 if rows else 0

    result["row_count"] = len(rows)
    result["assets_checked"] = assets_checked
    result["warnings"] = list(validation.get("warnings", []))
    if not rows:
        result["warnings"].append(
            {"path": str(root / "composite_ohlcv.json"), "code": "NO_COMPOSITE_OHLCV_ROWS_EXPORTED"}
        )

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(_rows_to_table(rows, pa), parquet_path)

    if validation.get("status") == "WARN" or result["warnings"]:
        result["status"] = "WARN"
    return result
