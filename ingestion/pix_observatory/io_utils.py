"""Helpers for writing partitioned Parquet datasets locally.

The directory layout mirrors what we'll use on S3 later:

    {root}/{source}/dt=YYYY-MM-DD/part-*.parquet

Same code path will work after we swap `pathlib.Path` for `s3fs` URIs.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import structlog

log = structlog.get_logger(__name__)


def partition_path(root: Path, source: str, dt: date) -> Path:
    """Return the partition directory for a given source and date."""
    return root / source / f"dt={dt.isoformat()}"


def write_records_parquet(
    records: Iterable[dict[str, Any]],
    *,
    root: Path,
    source: str,
    dt: date,
    filename: str = "part-0.parquet",
) -> Path:
    """Materialize an iterable of dict records as a single Parquet file.

    For now we keep it simple (single file per partition); a later Glue
    job will split into multiple parts for parallelism.
    """
    records_list = list(records)
    if not records_list:
        log.warning("write_records_parquet.empty", source=source, dt=dt.isoformat())
        return partition_path(root, source, dt)

    out_dir = partition_path(root, source, dt)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / filename

    table = pa.Table.from_pylist(records_list)
    pq.write_table(table, out_file, compression="snappy")

    log.info(
        "write_records_parquet.ok",
        source=source,
        dt=dt.isoformat(),
        rows=len(records_list),
        path=str(out_file),
    )
    return out_file
