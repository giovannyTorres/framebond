# Reproducible relational-validation benchmark

```bash
python benchmarks/benchmark.py --rows 100000 --repeat 5
```

The synthetic model contains 50,000 unique parent IDs and 100,000 uniquely keyed
child rows. Foreign keys cycle through 60,000 possible IDs, with a null every
997 rows. The default input has 9,990 orphan rows, 9,990 distinct missing keys
and 101 ignored null child keys. Both declared PKs are valid. The script asserts
these equivalent results from a separate manual Pandas recipe before timing.

The manual baseline uses isna, duplicated, isin and drop_duplicates to produce
PK validity and FK counts. The framebond workflow includes table registration
snapshots, reusable original-key indexes, relation configuration and all original
position issues. No full payload join is needed in either approach. This
comparison measures the complete library workflow rather than cached repeated
validate calls, so setup cost is included consistently.

Each workflow has one warmup followed by five perf_counter measurements.
Memory uses a separate tracemalloc execution: traced Python allocations exclude
some native allocation and are not process RSS. [results.json](results.json)
records the current environment, all timings, median/range, validated counts and
memory; it is authoritative after rerunning the command.

framebond is slower and uses more memory on the recorded dataset. Its additional
value is a reusable declaration/report workflow, original-value preservation and
positional diagnostics, not faster membership checks. Use the manual recipe for
a one-off validation when those extras are unnecessary. Results from one small
model do not predict every key distribution or graph of relations, and no
performance advantage is claimed.
