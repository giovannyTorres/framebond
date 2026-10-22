# framebond: measured benchmark results

Generated 2026-10-22T05:56:18.950586+00:00. CPython 3.13.5 on Windows-11-10.0.26200-SP0.

Exact versions: `framebond==0.2.0`, `pandas==3.0.6`, `numpy==2.5.4`.

5 rotating timed rounds after two warmups; 2 separate allocation passes. Data construction, assertions and printing are excluded from timings.

| Input size | Baseline ms | Package ms | Package / baseline | Baseline peak KiB | Package peak KiB |
|---:|---:|---:|---:|---:|---:|
| 1,000 | 1.143 | 5.150 | 4.51x | 49.9 | 604.3 |
| 10,000 | 1.975 | 41.428 | 20.98x | 391.3 | 6357.6 |
| 50,000 | 4.835 | 232.671 | 48.12x | 1793.9 | 32725.0 |

Ratio = package median / baseline median. Values above 1 mean higher latency. Peaks are traced Python allocations and exclude some native memory. Accuracy checks passed before every workload was timed.

The compared values/counts match. The package also produces validation, lineage or diagnostic metadata described in [the comparison](../docs/comparison.md); those extra outputs are not fully implemented by the baseline.

## Ease of use: inspectable code-size proxy

| Function | Physical lines (including signature) | AST statements |
|---|---:|---:|
| baseline | 4 | 3 |
| library | 6 | 5 |

These counts describe one checked example. They do not measure learning time, readability, debugging success or developer productivity. Both recipes remain available for review.

## Interpretation and limits

These are deterministic synthetic examples measured on one host. They support the stated input sizes and operations. They do not establish universal speed, statistical accuracy, behavior on every dtype, or parity with R packages. No R runtime was benchmarked. Larger keys, wider tables, more failures and expensive predicates can change costs substantially.

[Raw samples, checked outcomes, environment and source hashes](latest.json) · [Reproduction and workload definitions](README.md)
