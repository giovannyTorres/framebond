# Local validation record — framebond 0.2.0

Recorded 2026-10-21 (UTC) on Linux, Python 3.12.14. These are local
checks, separate from GitHub CI and public PyPI installation.

- 66 tests passed with both pandas 3.0.6 and pandas 2.2.3, including the
  Hypothesis suites; statement coverage was 100% (290/290 statements).
- Ruff lint/format and mypy passed. Wheel/sdist builds and Twine checks passed;
  both artifacts installed independently in clean virtual environments and ran
  the shipped examples with isolated imports.
- New regressions cover bool/number PK and FK separation, mixed/composite
  identifiers, string/number and aware/naive datetime diagnostics, nulls,
  original issue values, manually constructed KeyIndex lookups and custom
  adapters preserving nonboolean matching components.
- The existing 100,000-child/50,000-parent benchmark validated the same counts
  with pandas 3.0.6: 9,990 orphan rows/keys and 101 ignored nulls. Three timed
  samples gave a 0.707 s library median and 0.00859 s manual pandas median;
  these operations have different scopes, as documented below.

## Historical 0.1.0 validation

Recorded from completed local checks on 2026-10-21 (UTC).
These results are separate from GitHub CI and from public PyPI installation.

| Check | Observed result |
|---|---|
| Editable installation with development dependencies | Passed |
| Pytest and coverage threshold | Passed |
| Ruff lint | Passed |
| Ruff formatting | Passed |
| Mypy, src/ | Passed |
| Wheel and sdist build | Passed |
| Twine distribution metadata checks | Passed |
| Independent clean wheel and sdist installations and shipped examples | Passed |
| Benchmark execution | Passed |

**Tests:** 44 passed.
**Statement coverage:** 100.00% (231 of 231 measured statements; 3 excluded lines). This is not a branch-coverage claim.

Wheel and sdist were installed separately in fresh virtual environments with declared runtime dependencies.
The shipped examples ran with Python's `-I` flag, isolating imports from the repository checkout.
These installations used local distribution files, not a public-index upload.

## Recorded benchmark

Environment: python: `3.13.5`; pandas: `3.0.6`; platform: `Windows-11-10.0.26200-SP0`.

parent_rows: **50,000**; child_rows: **100,000**; repeats: **5**.

The complete validation workload registers 50,000 unique parent IDs and 100,000 uniquely keyed child rows. Foreign keys cycle through 60,000 IDs with a null every 997 rows. Before timing, a separate Pandas isna/duplicated/isin/drop_duplicates recipe and the library are asserted equal on both primary-key validity flags, 9,990 orphan rows, 9,990 distinct missing keys and 101 ignored null child keys. Each workflow warms up once and records five perf_counter durations. Table snapshots, registration, exact-key indexes and issue construction are included in the library workflow; a separate tracemalloc execution measures traced peak allocation without treating it as RSS.

| Workflow | Median seconds | Minimum–maximum seconds | Peak traced bytes |
|---|---:|---:|---:|
| `manual_pandas` | 0.018423 | 0.011740–0.021468 | 3,659,124 |
| `framebond` | 0.715159 | 0.611237–1.299505 | 56,987,063 |

Same primary-key validity and foreign-key counts checked before timing. Library includes registration snapshots, reusable exact-key indexes and original-position issues. Timing without tracemalloc; memory separately measured traced Python allocations, not RSS.

The [raw measurement file](benchmarks/results.json) is the source of these numbers.
See [benchmark code](benchmarks/benchmark.py) and its documented methodology for workload details.
`tracemalloc` figures, when present, are traced allocations rather than process RSS.
No universal performance advantage follows from a single workload.

## Reproduce

```bash
python -m pip install -e ".[dev]"
python -m pytest --cov=framebond --cov-report=term-missing --cov-fail-under=95
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m build
python -m twine check dist/*
python scripts/check_artifacts.py framebond
python benchmarks/benchmark.py
```

See [RELEASE.md](RELEASE.md) for publication status and the Trusted Publisher configuration.
