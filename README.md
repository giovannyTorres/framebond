# framebond

**Catch broken primary and foreign keys before loading your next batch.**

A CSV import can contain orders for missing customers, null identifiers or duplicate keys. framebond validates a set of DataFrames together and points back to the offending source positions.

## Try it in two minutes

Requires Python 3.11+ with pandas 2.2+. Install the [published release](https://pypi.org/project/framebond/0.2.0/):

```sh
python -m pip install "framebond==0.2.0"
```

Copy this complete example into a Python session or save it as `demo.py` and run `python demo.py`:

```python
import pandas as pd

from framebond import DataModel

customers = pd.DataFrame({"id": [1, 2]})
orders = pd.DataFrame({"id": [10, 11, 12], "customer_id": [1, 2, 3]})
model = DataModel().add_table("customers", customers, primary_key="id")
model.add_table("orders", orders, primary_key="id")
model.add_relation("orders.customer_id", "customers.id")
report = model.validate()
assert report.relations[0].orphan_rows == 1
print(report.explain())
print(report.issues(code="foreign_key_orphan"))
```

The example reports **one orphan order**: order 11 refers to missing customer 3.

## What you gain

Declare a multi-table model once, validate PK/FK/cardinality rules together, inspect original keys and row positions, and export strict JSON from the same report.

| Existing approach | What this package adds | Tradeoff |
|---|---|---|
| Pandas supplies `duplicated`, `isna`, `isin` and merge validation; Pandera and Frictionless offer broader schema validation. | Reusable cross-table constraints, all issue types in one report, type-mismatch diagnostics and original source keys/positions. | Model registration takes snapshots and validation builds indexes and issue tables. A single `isin` mask is simpler and usually cheaper for a one-off membership check. |

[Run the side-by-side comparison](docs/comparison.md): both implementations are included and their shared outputs are asserted equal. [dm](https://dm.cynkra.com/) inspires the relational-model workflow. framebond implements in-memory constraints and inspection; dm also supports database workflows outside this package's scope.

## Solve a real workflow problem

These small, synthetic operational fixtures make the workflows reproducible without external services or private records. Each recipe includes expected results and a failure or interpretation boundary.

| Recipe | Verified outcome |
|---|---|
| [Quarantine bad orders from an upload](docs/cookbook.md#find-bad-order-records) | Find orphan position 1 with `.iloc`, identify order 11, and report the null FK separately under nulls="forbid". |
| [Validate a many-to-many product/tag mapping](docs/cookbook.md#validate-product-tags) | Use a junction table with two foreign keys. The product relation passes and the tag relation reports one orphan. |
| [Keep large imported identifiers exact](docs/cookbook.md#preserve-exact-external-ids) | Construct object-backed identifiers, identify the adjacent orphan exactly and preserve its integer value in JSON. |

From a checkout, after installing the package:

```sh
python examples/comparison.py
python examples/cookbook.py
```

## Measured performance, accuracy and usability

Recorded on Windows-11-10.0.26200-SP0, CPython 3.13.5, with five rotating timed rounds. At the largest measured input size (50,000; see workload definition):

| Compared operation | Baseline median ms | Package median ms | Package / baseline |
|---|---:|---:|---:|
| Package / manual recipe | 4.835 | 232.671 | 48.12x |

Ratio = package median / baseline median; above 1 means higher latency. The package performs the extra diagnostic or provenance work described above. These single-host synthetic results have no universal speed guarantee. Allocation measurements and the smaller scales are in the full table.

[Measured table](benchmarks/RESULTS.md) · [Raw repeated samples](benchmarks/latest.json) · [Reproduction instructions](benchmarks/README.md)

Accuracy means agreement on the stated fixture outputs: PK validity plus orphan, distinct missing-key and null counts are checked exactly against a pandas recipe. Additional issue types are exercised by the cookbook and core tests. Code-size counts are an inspectable usability proxy; no developer-time study was performed.

## Scope and limits

- In-memory snapshots; no SQL execution, migrations, cascade operations or automatic repairs.
- FK targets must have unique nonnull keys. Generic many-to-many links use a junction table with two FKs.
- Boolean identifiers are distinct from numeric ones. A short pandas `isin` recipe may use different equality semantics on other dtypes.
- Large failure sets create large issue tables and JSON. Exact keys must be preserved when constructing inputs.

## Documentation

- [Start here](docs/index.md): choose a workflow and find the relevant guide.
- [Comparison and alternatives](docs/comparison.md): full code, shared behavior and added outputs.
- [Cookbook](docs/cookbook.md): three complete problem-solving recipes.
- [API and behavioral contracts](docs/api.md): exact semantics and errors.
- [Benchmark methodology](benchmarks/README.md): inputs, correctness checks, environment and limits.
- [Research and upstream credit](RESEARCH.md): R inspiration, existing Python tools and scope decisions.

## Develop and validate

```sh
python -m pip install -e ".[dev]"
python scripts/check_docs.py
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

MIT licensed. Contributions should include a reproducing example and the expected behavior. See [CONTRIBUTING.md](CONTRIBUTING.md).
