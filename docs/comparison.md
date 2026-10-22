# Comparison: framebond and the underlying primitives

A CSV import can contain orders for missing customers, null identifiers or duplicate keys. framebond validates a set of DataFrames together and points back to the offending source positions.

## What is compared

| Dimension | Scope |
|---|---|
| Existing tools | Pandas supplies `duplicated`, `isna`, `isin` and merge validation; Pandera and Frictionless offer broader schema validation. |
| Shared result checked | Positions of nonnull foreign keys absent from an integer-key parent table. The scale benchmark also compares PK validity, orphan rows, distinct missing keys and null rows. |
| Additional package behavior | Reusable cross-table constraints, all issue types in one report, type-mismatch diagnostics and original source keys/positions. |
| Cost / when a manual recipe fits | Model registration takes snapshots and validation builds indexes and issue tables. A single `isin` mask is simpler and usually cheaper for a one-off membership check. |

[dm](https://dm.cynkra.com/) inspires the relational-model workflow. framebond implements in-memory constraints and inspection; dm also supports database workflows outside this package's scope. The comparison below measures a Python workflow; it makes no claim of feature parity or numerical parity with an R package.

## Full executable example

Save this as `comparison.py` after installing the release, or run `python examples/comparison.py` from this repository. The assertions verify the stated shared result.

```python
"""Same orphan positions for integer keys; model adds reusable constraints."""

import pandas as pd

from framebond import DataModel


def baseline(customers, orders):
    key = orders["customer_id"]
    orphans = key.notna() & ~key.isin(customers["id"].dropna())
    return tuple(position for position, orphan in enumerate(orphans) if orphan)


def library(customers, orders):
    model = DataModel().add_table("customers", customers, primary_key="id")
    model.add_table("orders", orders, primary_key="id")
    model.add_relation("orders.customer_id", "customers.id")
    report = model.validate()
    return tuple(report.issues(code="foreign_key_orphan")["row_position"])


if __name__ == "__main__":
    customers = pd.DataFrame({"id": [1, 2]})
    orders = pd.DataFrame({"id": [10, 11, 12], "customer_id": [1, 9, None]})
    assert baseline(customers, orders) == library(customers, orders) == (1,)
    print("Both identify original position 1; the null FK is exempt by policy.")
```

## How to choose

Use the package when you need its named diagnostics, explicit policies or provenance repeatedly. Keep the underlying pandas/Python recipe when that smaller shared result meets the job. Review each recipe's data assumptions before applying it to another dtype or layout.

Model registration takes snapshots and validation builds indexes and issue tables. A single `isin` mask is simpler and usually cheaper for a one-off membership check.

## Evidence and boundaries

PK validity plus orphan, distinct missing-key and null counts are checked exactly against a pandas recipe. Additional issue types are exercised by the cookbook and core tests.

The baseline checks shared counts only. It does not construct the model snapshots, issue rows or type diagnostics produced by the package. Many failures and wider composite keys change costs. Timing differences do not establish statistical accuracy or developer productivity. The benchmark checks exact fixture outputs and separately reports code-size counts as a limited usability proxy.

[Actual measured results](../benchmarks/RESULTS.md) · [Reproduce the benchmark](../benchmarks/README.md) · [Recipes](cookbook.md) · [API contracts](api.md)

## Sources and alternatives

- [pandas API documentation](https://pandas.pydata.org/docs/reference/index.html) documents the underlying grouping, masking and reshaping primitives.
- [dm relational modeling and constraint checking](https://dm.cynkra.com/)
- [Pandera documentation](https://pandera.readthedocs.io/en/stable/)
- [Frictionless table schemas](https://specs.frictionlessdata.io/table-schema/)

Upstream references credit problem ideas and existing tools. This repository contains its own implementation and claims no upstream affiliation.
