# Changelog

## 0.2.0 — 2026-10-21

- Keep boolean identifiers distinct from numeric identifiers in primary-key
  uniqueness and foreign-key membership, including mixed/composite object keys.
  Numeric `1` and `1.0` still match, and source keys remain unchanged in issues.
- Explain incompatible orphan key types through `RelationResult.type_mismatches`,
  `foreign_key_type_mismatch` issues and the text/JSON reports. This includes
  string/number identifiers and timezone-aware/naive datetimes; no coercion occurs.
- Add `KeyIndex.positions_for(original_key)` for type-aware position lookup.
  Boolean components in the lower-level `positions` mapping now use internal
  matching tokens. Custom backend results are normalized at the model boundary.
- Add regressions and generated mixed-type membership checks.

## 0.1.0 — 2026-10-21

- Initial independently installable release of framebond.
- Typed public API, original implementations, executable examples, tests, and reproducible benchmarks.

Publication state is recorded in RELEASE.md; this version number alone does not imply a PyPI upload.
