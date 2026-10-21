# framebond

Validate primary keys, foreign keys and cardinality across Pandas DataFrames.
Keep original key values, row positions and index labels in inspectable issues,
then export strict JSON without requiring a database.

```python
import pandas as pd
from framebond import DataModel

customers = pd.DataFrame({"id": [1, 2]})
orders = pd.DataFrame({"id": [10, 11], "customer_id": [1, 3]})
model = DataModel().add_table("customers", customers, primary_key="id")
model.add_table("orders", orders, primary_key="id")
model.add_relation("orders.customer_id", "customers.id")
print(model.validate().explain())
```

This reports one orphan order referencing customer 3. Model setup and validation
fit in four API calls after creating the frames.

## Install

Python 3.11+ and Pandas 2.2+ are required. Version
[0.1.0 is published on PyPI](https://pypi.org/project/framebond/0.1.0/), with
installation from the public index verified in a fresh environment.

```bash
python -m pip install framebond
# Reproduce the verified release:
python -m pip install "framebond==0.1.0"
```

No runtime service, telemetry, database or sibling-project dependency is used.

## API

| API | Behavior |
|---|---|
| `DataModel()` | Create an empty model |
| `model.add_table(name, frame, primary_key=None)` | Register a snapshot and optional single/composite PK; returns model |
| `model.add_relation(child, parent, name=None, nulls="ignore", relationship="many_to_one")` | Declare an FK and optional child uniqueness; returns model |
| `model.validate()` | Return a `ValidationReport`; no joined payload is materialized |
| `report.valid` | True if all declared constraints hold |
| `report.tables` / `report.relations` | Ordered tuples of typed `TableResult` / `RelationResult` |
| `report.issues(table=None, relation=None, code=None)` | Fresh native DataFrame with optional exact filters |
| `report.explain()` | Human-readable summary |
| `report.to_dict()` / `report.to_json(indent=2)` | Structured JSON-native results including issues |

Table names are unique nonempty strings without dots. Frames require unique
flat column labels. Key columns are distinct existing strings. A primary key
may be `"id"` or `["tenant", "id"]`. Invalid configuration raises `ModelError`;
non-DataFrame table input raises `TypeError`. Invalid data constraints appear in
the report, allowing all failures to be reviewed together.

Tables are copied at registration. Later edits to caller frames do not change
the model; create a new model to validate updated data. No transformation or
in-place cleanup occurs. Snapshot copies do not recursively clone mutable
objects inside unrelated payload cells; keys themselves must be hashable scalars.

## Composite references and cardinality

Single-column references use `"orders.customer_id"`. Composite references are
explicit tuples of table name and ordered columns:

```python
model.add_relation(
    ("orders", ["tenant", "customer_id"]), ("customers", ["tenant", "id"]), nulls="forbid"
)
```

The example assumes both named tables and columns were registered first.
Child and target column counts must agree. Repeated relation names are rejected;
use `name=...` when declaring distinct policies on the same columns.

Every FK requires **unique nonnull target keys**, even when those columns were
not declared as a PK. `relationship="many_to_one"`, the default, permits repeated
nonnull child keys. `relationship="one_to_one"` additionally requires unique
nonnull child keys. A stricter observed one-to-one relation satisfies the
many-to-one rule. Generic one-to-many/many-to-many link validation is outside
this FK API; model a junction table with two FKs instead.

`observed_relationship` describes nonnull uniqueness across the complete child
and parent inputs, including unmatched keys. It is separate from FK membership:
a relationship can have expected cardinality and still contain orphans. Parent
rows need not all be referenced, and minimum participation is not enforced.

## Nulls, equality and exact values

Default `nulls="ignore"` follows SQL MATCH SIMPLE-style behavior: **any** null
component makes a composite child key exempt from membership checks. With
`nulls="forbid"`, every such row is a `foreign_key_null` issue. Null child rows
are counted separately from orphans; they are never matched to null parent rows.
Parent any-null keys are excluded from matching and nonnull uniqueness checks.
If a parent PK is declared, its nulls still invalidate that table's PK.

Declared PKs reject any-null keys and repeated nonnull keys. `duplicate_rows`
counts all nonnull rows participating in duplicate groups, not just excess
copies; `duplicate_keys` counts distinct duplicated nonnull keys. Null rows are
counted separately. An undeclared PK has `primary_key_valid=None` and zero PK
issue counts, rather than an inferred constraint.

Matching uses original scalar tuples and Python hash/equality. Numeric 1 and
1.0 match; string `"1"` is distinct. Types are never normalized or silently cast.
Containers used as key values are rejected; composite keys belong in multiple
explicit columns. Object-backed adjacent large integers retain identity even
beside nulls. Precision already lost while constructing a DataFrame cannot be
recovered. Normalize application-specific identifiers explicitly before
registration when needed.

## Issues and strict JSON

Native issue columns are `scope`, `table`, `relation`, `code`, `row_position`,
`index`, and `key`. `key` contains original scalar tuples. Positions are original
zero-based table rows, independent of duplicate/nonstandard index labels.
Issues follow constraint order and then source position within each constraint.
They can be used to retrieve source records with `.iloc`.

| Issue code | Meaning |
|---|---|
| `primary_key_null` | Declared PK has a null component |
| `primary_key_duplicate` | Nonnull declared PK repeats |
| `foreign_key_orphan` | Nonnull child key is absent from target |
| `foreign_key_target_duplicate` | Nonnull target key repeats |
| `foreign_key_null` | Child has any null component under `forbid` |
| `relation_child_duplicate` | Nonnull child key repeats under `one_to_one` |

`RelationResult.orphan_rows` includes every orphan record; `missing_keys` counts
distinct absent nonnull keys. Counts differ when an absent reference repeats.
Use `report.issues(code="foreign_key_orphan")` to inspect those native values.

`to_dict()` returns JSON-compatible structures. Integers retain their exact
numeric values, missing values become null, dates/times use ISO strings and
tuples become JSON arrays. Decimal/UUID/duration/byte values use explicit type
tags and string/hex payloads. Nonfinite floats use tagged string values, never
invalid JSON numeric literals. NumPy temporal scalars preserve temporal type
and nanosecond duration values. Other supported scalar objects use a type tag
and textual representation. JSON is an inspection/export format, not a full
round-trip model serializer; native issue frames preserve original objects.

## Alternatives, scope and architecture

[dm](https://github.com/cynkra/dm) inspired the relational-model approach.
Frictionless already defines PK/FK schemas; Pandera and Great Expectations
already provide strong validation tools. Pandas and Polars supply uniqueness
and membership primitives. framebond focuses on a small direct-DataFrame API,
exact source keys and positional issue inspection. See [RESEARCH.md](RESEARCH.md)
for comparisons, evidence and upstream licenses.

Version 0.1.0 supports in-memory Pandas snapshots. It does not implement an ORM,
migrations, SQL execution, cascading changes, type coercion, generic graph-link
constraints or automatic key discovery. Snapshot/index storage is proportional
to input rows and key width; issue storage can also be large when many rows
fail. Full issue JSON can be expensive. The small `KeyBackend` protocol isolates
original key extraction/indexing for future adapters; the implemented backend
is Pandas only. Its equality/null policies must be revisited explicitly for
other backends.

## Validation and benchmark

```bash
python -m pip install -e ".[dev]"
python -m pytest --cov=framebond --cov-report=term-missing
python -m ruff check .
python -m mypy src
python examples/quickstart.py
python examples/composite_and_json.py
python benchmarks/benchmark.py --rows 100000 --repeat 5
```

Tests use independent Counter/set references, generated composite/null keys,
empty tables, duplicate indices, exact large integers, original scalar/date
JSON regressions and validation with DataFrame.merge forbidden. The benchmark
uses 50,000 parent and 100,000 child rows, checks equivalent manual Pandas counts,
and records five timed samples after warmup plus separate traced memory.
[Raw results](benchmarks/results.json) and [methodology](benchmarks/README.md)
document the extra cost of snapshots, reusable indexes and native issues.

See [CONTRIBUTING.md](CONTRIBUTING.md). Original code is MIT licensed with credit
to upstream inspiration and no affiliation claim. Proposed 0.2.0 priorities:
bounded issue samples, explicit expected dtype policies, incremental validation
and a separately verified alternate backend.
