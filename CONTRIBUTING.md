# Contributing

Use Python 3.11 or newer. Open an issue with a small reproducible example before proposing a large API change.
Never attach private source data or credentials. Small synthetic DataFrames make good bug reports.

```bash
python -m venv .venv
# Activate .venv with the command appropriate for your shell.
python -m pip install -e ".[dev]"
python -m pytest --cov=framebond --cov-report=term-missing --cov-fail-under=95
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m build
python -m twine check dist/*
python scripts/check_artifacts.py framebond
```

Include regression tests for fixes. Test results against an independent Pandas or Python reference where practical.
Preserve input values, indexes, and row order unless an operation explicitly documents a transformation.
Document null semantics and ambiguous cases. Public functions need annotations and useful error messages.
Keep optional integrations optional; importing the package must not perform network or filesystem operations.

The CI matrix checks Python 3.11–3.14 with the latest supported Pandas and a Python 3.11/Pandas 2.2.3 floor.
Benchmarks report repeated measurements; they are not timing assertions in CI.
Contributions are distributed under the project's MIT license.
