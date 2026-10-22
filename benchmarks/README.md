# Reproduce the framebond benchmarks

[Measured results](RESULTS.md) · [Raw measurements](latest.json) · [Driver](reproduce.py)

## One-command measurement

Clone this repository and use CPython 3.13.5 to reproduce the recorded environment. From the repository root:

```sh
python -m pip install -r benchmarks/requirements.txt
python benchmarks/reproduce.py
```

The requirements file pins the public package and runtime dependencies measured in this run. To benchmark a changed checkout instead, install it with `python -m pip install -e .` after those pins and record that difference. The driver records the imported distribution version, base commit and SHA-256 digests of the benchmark and example sources with line endings normalized to LF.

The default run writes `benchmarks/latest.json` and regenerates `benchmarks/RESULTS.md`. It runs all comparison and cookbook assertions first, then checks each timed workload against its reference. A failing comparison aborts before publishing new measurements.

```sh
# Small correctness/runner smoke check; writes only ignored smoke.json:
python benchmarks/reproduce.py --quick
# More observations on the same three sizes:
python benchmarks/reproduce.py --repeat 9
```

## Inputs and equivalent work

n//2 parent rows, n child rows and one FK. Every 997th child FK is null; the nonnull domain extends beyond the parent domain, producing controlled orphans.

The input generator is deterministic and included in the driver. Input construction, package imports, correctness assertions and output serialization are outside the measured operation. The fixture setup and reused state are the same for both compared operations.

PK validity plus orphan, distinct missing-key and null counts are checked exactly against a pandas recipe. Additional issue types are exercised by the cookbook and core tests.

The baseline checks shared counts only. It does not construct the model snapshots, issue rows or type diagnostics produced by the package. Many failures and wider composite keys change costs.

## Timing and memory

- Two warmups per operation, then five timed rounds by default.
- Interleaved operations with a rotating starting order reduce fixed-order drift.
- `perf_counter` measures elapsed time; garbage collection happens before each sample and outside its timer.
- The standard paired driver retains the returned object until the timer stops. The whyempty six-scenario driver times batches of three operations; its full implementation is in benchmark.py.
- Allocation peaks use two separate `tracemalloc` passes with a live result. They exclude the already constructed inputs and can exclude native allocations; they are not total process RSS.
- Raw observations, medians, minimum/maximum times, package/Python/platform/CPU details and checked fixture outcomes are in latest.json. Whyempty retains the original six-scenario raw schema and computes its medians there.

Run on an otherwise idle machine. Results vary with host load, CPU state, allocator, Python, dependency versions, data cardinality, width and dtype. These are single-host measurements with no confidence intervals. They are not service-level guarantees or a comparison against every possible optimized recipe.

## Accuracy and ease of use

Accuracy here means asserted agreement on the documented output fields, not a statistical significance claim or proof over all inputs. The core tests cover additional boundary cases and can be rerun with `python -m pip install -e ".[dev]"` followed by `python -m pytest`.

The driver counts physical lines and AST statements in the checked comparison functions. Fixtures, imports and assertion scaffolding are excluded. This code-size proxy is inspectable; it does not measure learning time or productivity. The library may perform more diagnostic work and may take more source lines in a given example.

## Historical and specialized runs

The original `benchmark.py` and `results.json` are retained with their original workload and environment. `RESULTS.md` and `latest.json` identify the new measurements. Other benchmark scripts in this directory cover specialized cases and are not silently combined into the main table.

Model registration takes snapshots and validation builds indexes and issue tables. A single `isin` mask is simpler and usually cheaper for a one-off membership check.

[What the package adds](../docs/comparison.md) · [Practical recipes](../docs/cookbook.md)
