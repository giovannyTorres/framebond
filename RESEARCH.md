# Research and scope decision

Reviewed 2026-10-21. Original Python implementation; no R code was copied or
translated. `relcheck` was explicitly excluded because the requested name is
already registered to another PyPI project.

| Capability | R implementation | Python alternatives | Gap | Proposed solution |
|---|---|---|---|---|
| Multi-table constraints | [dm](https://github.com/cynkra/dm) models related tables and validates declared keys | [Frictionless Schema](https://framework.frictionlessdata.io/docs/framework/schema.html) already has primary_key and foreign_keys metadata | Relational validation is already solved; a narrow direct-DataFrame API can reduce setup | DataModel snapshots, explicit key references and one structured report |
| Primary-key uniqueness/nulls | dm key declarations and [dm_examine_constraints](https://dm.cynkra.com/reference/dm_examine_constraints.html) | [Pandera schemas/checks](https://pandera.readthedocs.io/en/stable/dataframe_schemas.html), [GX uniqueness expectations](https://docs.greatexpectations.io/docs/reference/learn/data_quality_use_cases/uniqueness/), Pandas duplicated/isna | No novelty claim for basic validation | Consistent positional issue rows and exact native keys |
| Foreign-key membership | dm constraint examination | Frictionless foreign_keys; Pandera custom checks; Pandas membership operations | Explicit null/target uniqueness rules and composite issue bookkeeping need assembly | Any-null child policy, distinct missing-key count and all orphan row positions |
| Cardinality | [dm examine_cardinality](https://dm.cynkra.com/reference/examine_cardinality.html) checks uniqueness, inclusion and requested multiplicity | Pandas merge validate and [Polars join validate](https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.join.html) enforce join uniqueness | Join cardinality and a valid foreign key are different requirements | Target uniqueness always required; optional child uniqueness for one-to-one |
| Diagnostics/export | dm returns structured diagnostics | General validation frameworks already offer reports | Native key/index preservation and strict JSON need explicit conversion rules | Typed results, native issue frames, exact integers, ISO dates and tagged special scalars |

## Evidence and positioning

This is a small convenience and reproducibility API, not a claim that Python
cannot validate relational data. Frictionless provides relational schema
capabilities, Pandera provides powerful DataFrame schemas/custom checks, and GX
provides a broader expectation framework. framebond focuses on a few related
Pandas frames with minimal runtime dependencies and original positional issues.

The requested CRAN reference
`https://search.r-project.org/CRAN/refmans/dm/help/examine_cardinality.html`
redirects; the package's current official reference above was read directly.
dm supports richer multiplicity requirements and database workflows than this
release. framebond does not implement general link relationships, an ORM,
migrations, joins or database persistence.

Tests compare PK and FK results against independent Python Counter/set
references, generate composite partial-null keys, and check exact adjacent
integers above 2**53. Native issues retain original positions despite duplicate
indices. A regression forbids DataFrame.merge during validation, demonstrating
that duplicate keys do not allocate a many-to-many payload result. The benchmark
validates 100,000 child rows and compares an explicit manual Pandas recipe.

## Exact-key and null semantics

Scalar key tuples are indexed directly from original cells. No inferred group
index, string normalization or numeric cast is used. Matching follows Python
hash/equality on nonnull scalar tuples: numeric 1 and 1.0 agree, string "1"
does not. Any-null parent keys are excluded from membership. Any-null child
keys are ignored by default (SQL MATCH SIMPLE style) or rejected explicitly.
Target nonnull keys must be unique even if no primary key was declared.
Null parent rows are independently invalid if they belong to a declared PK.

## Licenses

[dm DESCRIPTION](https://github.com/cynkra/dm/blob/main/DESCRIPTION) declares the
MIT license plus a license file. [Pandera](https://github.com/unionai-oss/pandera/blob/main/LICENSE.txt)
and [Frictionless](https://github.com/frictionlessdata/frictionless-py/blob/main/LICENSE.md)
use MIT. [GX Core](https://github.com/great-expectations/great_expectations/blob/develop/LICENSE)
uses Apache-2.0. Pandas uses BSD-3-Clause and Polars uses MIT. Only public API
behavior and problem scope informed this code; no source was reused. framebond
original code uses MIT and claims no affiliation with these projects.

## Naming

On 2026-10-21, `https://pypi.org/pypi/framebond/json` returned HTTP 404.
PEP 503 normalization leaves `framebond` unchanged. GitHub public repository
search `framebond in:name` returned one substring match,
`framebonds-maker/framebonds`, with no exact `framebond` match. The name describes
constraints bonding frames and differs from occupied `relcheck`. These are
visible collision checks, not a name reservation or legal trademark clearance.
Recheck immediately before publication; a missing PyPI page does not guarantee
registration.
