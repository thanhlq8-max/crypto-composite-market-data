"""Parquet export mirrors the CSV export with typed columns; pyarrow stays optional."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from crypto_composite.artifact_csv import write_composite_ohlcv_csv
from crypto_composite.artifact_parquet import (
    PARQUET_COLUMNS,
    ParquetDependencyError,
    write_composite_ohlcv_parquet,
)
from tests.test_artifact_csv import _write_single_asset


def test_missing_pyarrow_raises_dependency_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    with pytest.raises(ParquetDependencyError, match="PARQUET_DEPENDENCY_MISSING"):
        write_composite_ohlcv_parquet(tmp_path, tmp_path / "out.parquet")


def test_parquet_export_matches_csv_rows(tmp_path: Path) -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")

    root = tmp_path / "artifacts"
    _write_single_asset(root)
    csv_result = write_composite_ohlcv_csv(root, tmp_path / "out.csv")
    parquet_result = write_composite_ohlcv_parquet(root, tmp_path / "out.parquet")

    assert parquet_result["status"] in {"OK", "WARN"}
    assert parquet_result["row_count"] == csv_result["row_count"] > 0
    assert parquet_result["assets_checked"] == csv_result["assets_checked"]

    table = pq.read_table(tmp_path / "out.parquet")
    assert table.num_rows == csv_result["row_count"]
    assert table.column_names == list(PARQUET_COLUMNS)
    assert table.schema.field("timestamp_ms").type == pa.int64()
    assert table.schema.field("close").type == pa.float64()
    assert table.schema.field("venue_weights_json").type == pa.string()

    spot = table.to_pylist()[0]
    assert spot["asset"] == "BTC-USDT"
    assert spot["timestamp_ms"] == 1699999100000
    assert spot["venue_count"] == 3


def test_parquet_export_empty_root_reports_error(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    result = write_composite_ohlcv_parquet(tmp_path, tmp_path / "out.parquet")
    assert result["status"] == "ERROR"
    assert result["errors"]
