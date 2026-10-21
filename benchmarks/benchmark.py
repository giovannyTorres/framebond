"""Compare a complete model validation with a manual Pandas constraint recipe."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from framebond import DataModel


def manual(parent: pd.DataFrame, child: pd.DataFrame) -> dict[str, int | bool]:
    """Independent Pandas recipe: PK nulls/duplicates and FK exact membership."""
    parent_null = parent["id"].isna()
    child_null = child["id"].isna()
    parent_duplicates = parent["id"].duplicated(keep=False) & ~parent_null
    child_duplicates = child["id"].duplicated(keep=False) & ~child_null
    fk_null = child["customer_id"].isna()
    orphan = ~fk_null & ~child["customer_id"].isin(parent.loc[~parent_null, "id"])
    return {
        "parent_pk_valid": not bool(parent_null.any() or parent_duplicates.any()),
        "child_pk_valid": not bool(child_null.any() or child_duplicates.any()),
        "orphan_rows": int(orphan.sum()),
        "missing_keys": len(child.loc[orphan, "customer_id"].drop_duplicates()),
        "null_rows": int(fk_null.sum()),
    }


def library(parent: pd.DataFrame, child: pd.DataFrame) -> Any:
    model = DataModel().add_table("customers", parent, primary_key="id")
    model.add_table("orders", child, primary_key="id")
    model.add_relation("orders.customer_id", "customers.id")
    return model.validate()


def measure(operation: Callable[[], object], repeats: int) -> dict[str, object]:
    operation()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        operation()
        samples.append(time.perf_counter() - start)
    tracemalloc.start()
    operation()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "seconds": samples,
        "median_seconds": statistics.median(samples),
        "min_seconds": min(samples),
        "max_seconds": max(samples),
        "traced_peak_bytes": peak,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results.json"))
    args = parser.parse_args()
    if args.rows < 100 or args.repeat < 2:
        parser.error("rows must be >=100 and repeat >=2")
    parent = pd.DataFrame({"id": range(args.rows // 2)})
    child = pd.DataFrame(
        {
            "id": range(args.rows),
            "customer_id": pd.Series(
                [
                    None if row % 997 == 0 else row % (args.rows * 3 // 5)
                    for row in range(args.rows)
                ],
                dtype=object,
            ),
        }
    )
    reference = manual(parent, child)
    report = library(parent, child)
    assert reference == {
        "parent_pk_valid": report.tables[0].primary_key_valid,
        "child_pk_valid": report.tables[1].primary_key_valid,
        "orphan_rows": report.relations[0].orphan_rows,
        "missing_keys": report.relations[0].missing_keys,
        "null_rows": report.relations[0].null_rows,
    }
    result = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "parent_rows": len(parent),
        "child_rows": len(child),
        "repeats": args.repeat,
        "validated_counts": reference,
        "manual_pandas": measure(lambda: manual(parent, child), args.repeat),
        "framebond": measure(lambda: library(parent, child), args.repeat),
        "notes": "Same primary-key validity and foreign-key counts checked before timing. Library includes registration snapshots, reusable exact-key indexes and original-position issues. Timing without tracemalloc; memory separately measured traced Python allocations, not RSS.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
