"""Declarative relational constraints on immutable DataFrame snapshots."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from numbers import Integral, Real
from typing import Any, Literal, Protocol
from uuid import UUID

import pandas as pd

Columns = str | Sequence[str]
Reference = str | tuple[str, Columns]
NullPolicy = Literal["ignore", "forbid"]
Relationship = Literal["many_to_one", "one_to_one"]


class ModelError(ValueError):
    """Invalid model configuration or unsupported key data."""


def _is_null(value: Any) -> bool:
    return pd.api.types.is_scalar(value) and bool(pd.isna(value))


def _columns(frame: pd.DataFrame, columns: Columns) -> tuple[str, ...]:
    try:
        selected = (columns,) if isinstance(columns, str) else tuple(columns)
    except TypeError as exc:
        raise ModelError("Keys must be a string or sequence of string column names") from exc
    if (
        not selected
        or not all(isinstance(column, str) for column in selected)
        or len(set(selected)) != len(selected)
        or any(column not in frame.columns for column in selected)
    ):
        raise ModelError("Keys require one or more distinct existing string column names")
    return selected


@dataclass(frozen=True)
class KeyIndex:
    """Backend-neutral original keys, null positions and nonnull key positions."""

    keys: tuple[tuple[Any, ...], ...]
    null_positions: tuple[int, ...]
    positions: dict[tuple[Any, ...], tuple[int, ...]]

    @property
    def duplicate_positions(self) -> tuple[int, ...]:
        """All positions participating in a nonnull duplicate key, in row order."""
        return tuple(
            sorted(
                pos
                for positions in self.positions.values()
                if len(positions) > 1
                for pos in positions
            )
        )

    @property
    def duplicate_keys(self) -> int:
        """Number of distinct nonnull keys occurring more than once."""
        return sum(len(positions) > 1 for positions in self.positions.values())


class KeyBackend(Protocol):
    """Small adapter boundary for original scalar key extraction and indexing."""

    def index(self, frame: pd.DataFrame, columns: tuple[str, ...]) -> KeyIndex:
        """Read original values without inferred group labels or payload joins."""
        ...


class PandasBackend:
    """Original scalar tuple equality, with any scalar null excluded from matching."""

    def index(self, frame: pd.DataFrame, columns: tuple[str, ...]) -> KeyIndex:
        keys = tuple(frame.loc[:, list(columns)].itertuples(index=False, name=None))
        nulls: list[int] = []
        positions: dict[tuple[Any, ...], list[int]] = {}
        for pos, key in enumerate(keys):
            if any(not pd.api.types.is_scalar(value) for value in key):
                raise ModelError(f"Key values must be hashable scalars; invalid row position {pos}")
            if any(_is_null(value) for value in key):
                nulls.append(pos)
                continue
            try:
                positions.setdefault(key, []).append(pos)
            except TypeError as exc:
                raise ModelError(f"Unhashable key at row position {pos}") from exc
        return KeyIndex(keys, tuple(nulls), {key: tuple(rows) for key, rows in positions.items()})


@dataclass
class _Table:
    frame: pd.DataFrame
    primary_key: tuple[str, ...] | None
    indexes: dict[tuple[str, ...], KeyIndex] = field(default_factory=dict)

    def index(self, columns: tuple[str, ...], backend: KeyBackend) -> KeyIndex:
        if columns not in self.indexes:
            self.indexes[columns] = backend.index(self.frame, columns)
        return self.indexes[columns]


@dataclass(frozen=True)
class TableResult:
    """Primary-key result; undeclared keys have primary_key_valid=None."""

    name: str
    rows: int
    primary_key: tuple[str, ...] | None
    primary_key_valid: bool | None
    null_rows: int
    duplicate_rows: int
    duplicate_keys: int


@dataclass(frozen=True)
class RelationResult:
    """Foreign-key membership and uniqueness results for one declared relation."""

    name: str
    child_table: str
    parent_table: str
    child_columns: tuple[str, ...]
    parent_columns: tuple[str, ...]
    nulls: NullPolicy
    relationship: Relationship
    observed_relationship: str
    null_rows: int
    orphan_rows: int
    missing_keys: int
    target_duplicate_keys: int
    child_duplicate_keys: int
    valid: bool


@dataclass(frozen=True)
class _Relation:
    name: str
    child_table: str
    child_columns: tuple[str, ...]
    parent_table: str
    parent_columns: tuple[str, ...]
    nulls: NullPolicy
    relationship: Relationship


@dataclass(frozen=True)
class Issue:
    """A failing row, original index label and unmodified key tuple."""

    scope: str
    table: str
    relation: str | None
    code: str
    row_position: int
    index: Any
    key: tuple[Any, ...]


def _native(value: Any) -> Any:
    """Strict JSON values, keeping exact integers and explicitly tagged exceptions."""
    if value is None or _is_null(value):
        return None
    if isinstance(value, (str, bool)):
        return value
    # numpy.timedelta64 can satisfy numbers.Integral, so preserve its temporal
    # type before the generic numeric branches.
    if type(value).__module__.startswith("numpy") and type(value).__name__ == "datetime64":
        return pd.Timestamp(value).isoformat()
    if type(value).__module__.startswith("numpy") and type(value).__name__ == "timedelta64":
        return {"type": "timedelta64", "value": pd.Timedelta(value).isoformat()}
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        return number if math.isfinite(number) else {"type": "float", "value": str(number)}
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID, timedelta)):
        return {"type": type(value).__name__, "value": str(value)}
    if isinstance(value, bytes):
        return {"type": "bytes", "value": value.hex()}
    if isinstance(value, dict):
        return {str(key): _native(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_native(item) for item in value]
    if type(value).__module__.startswith("numpy") and hasattr(value, "item"):
        return _native(value.item())
    return {"type": f"{type(value).__module__}.{type(value).__qualname__}", "value": str(value)}


@dataclass(frozen=True)
class ValidationReport:
    """Ordered results and original row-level issues for one validation run."""

    tables: tuple[TableResult, ...]
    relations: tuple[RelationResult, ...]
    _issues: tuple[Issue, ...] = field(repr=False)

    @property
    def valid(self) -> bool:
        """True exactly when every declared constraint holds."""
        return all(table.primary_key_valid is not False for table in self.tables) and all(
            relation.valid for relation in self.relations
        )

    def issues(
        self,
        *,
        table: str | None = None,
        relation: str | None = None,
        code: str | None = None,
    ) -> pd.DataFrame:
        """Return fresh native issue rows, optionally filtered by exact metadata.

        Positions refer to original table registration order, independent of
        index labels. Constraint order is deterministic; rows within each
        constraint retain original positional order.
        """
        records = [
            asdict(issue)
            for issue in self._issues
            if (table is None or issue.table == table)
            and (relation is None or issue.relation == relation)
            and (code is None or issue.code == code)
        ]
        return pd.DataFrame(
            records,
            columns=["scope", "table", "relation", "code", "row_position", "index", "key"],
            dtype=object,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-native structured results, including all row-level issues."""
        return {
            "valid": self.valid,
            "tables": [_native(asdict(table)) for table in self.tables],
            "relations": [_native(asdict(relation)) for relation in self.relations],
            "issues": [_native(asdict(issue)) for issue in self._issues],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize strict JSON with no NaN or Infinity numeric literals."""
        return json.dumps(self.to_dict(), indent=indent, allow_nan=False)

    def explain(self) -> str:
        """Return a human-readable summary calculated from actual constraints."""
        lines = [
            "RELATIONAL INTEGRITY REPORT",
            f"Tables: {len(self.tables)}",
            f"Relations: {len(self.relations)}",
            f"Overall: {'VALID' if self.valid else 'INVALID'}",
        ]
        for table in self.tables:
            status = (
                "NOT DECLARED"
                if table.primary_key_valid is None
                else "VALID"
                if table.primary_key_valid
                else "INVALID"
            )
            lines.append(
                f"{table.name}: Primary key {status}; null rows {table.null_rows}; duplicate rows {table.duplicate_rows}"
            )
        for relation in self.relations:
            lines.extend(
                [
                    f"{relation.child_table} -> {relation.parent_table}: Foreign key {'VALID' if relation.valid else 'INVALID'}",
                    f"Orphan records: {relation.orphan_rows}; Missing references: {relation.missing_keys} unique keys",
                    f"Relationship: {relation.observed_relationship}; required {relation.relationship}",
                ]
            )
        return "\n".join(lines)


class DataModel:
    """Register table snapshots and validate primary/foreign-key constraints.

    Data is copied at add_table time. Later caller edits do not affect the model.
    Foreign keys always require unique nonnull target keys. Many-to-many link
    modeling is intentionally outside this foreign-key API.
    """

    def __init__(self) -> None:
        self._tables: dict[str, _Table] = {}
        self._relations: dict[str, _Relation] = {}
        self._backend: KeyBackend = PandasBackend()

    def add_table(
        self, name: str, frame: pd.DataFrame, *, primary_key: Columns | None = None
    ) -> DataModel:
        """Add a snapshot and optional single/composite primary key; return self."""
        if not isinstance(name, str) or not name or "." in name or name in self._tables:
            raise ModelError("Table names must be new nonempty strings without dots")
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame")
        if not frame.columns.is_unique or isinstance(frame.columns, pd.MultiIndex):
            raise ModelError("Tables require unique flat column labels")
        keys = _columns(frame, primary_key) if primary_key is not None else None
        table = _Table(frame.copy(deep=True), keys)
        if keys is not None:
            table.index(keys, self._backend)
        self._tables[name] = table
        return self

    def _reference(self, reference: Reference) -> tuple[str, tuple[str, ...]]:
        name: str
        columns: Columns
        if isinstance(reference, str) and "." in reference:
            name, columns = reference.split(".", 1)
        elif isinstance(reference, tuple) and len(reference) == 2 and isinstance(reference[0], str):
            name, columns = reference
        else:
            raise ModelError("References must be 'table.column' or ('table', ['column', ...])")
        if name not in self._tables:
            raise ModelError(f"Unknown table {name!r}")
        return name, _columns(self._tables[name].frame, columns)

    def add_relation(
        self,
        child: Reference,
        parent: Reference,
        *,
        name: str | None = None,
        nulls: NullPolicy = "ignore",
        relationship: Relationship = "many_to_one",
    ) -> DataModel:
        """Add a foreign key with SQL MATCH SIMPLE-style ignore or forbid nulls.

        Any-null child keys are ignored by default. Nonnull parent keys must be
        unique whether or not they were declared as that table's primary key.
        """
        if nulls not in {"ignore", "forbid"} or relationship not in {"many_to_one", "one_to_one"}:
            raise ModelError(
                "nulls must be ignore/forbid; foreign-key relationship must be many_to_one/one_to_one"
            )
        child_table, child_columns = self._reference(child)
        parent_table, parent_columns = self._reference(parent)
        if len(child_columns) != len(parent_columns):
            raise ModelError("Foreign-key and target column counts must agree")
        label = (
            name
            if name is not None
            else f"{child_table}({','.join(child_columns)})->{parent_table}({','.join(parent_columns)})"
        )
        if not isinstance(label, str) or not label or label in self._relations:
            raise ModelError("Relation names must be new nonempty strings")
        self._tables[child_table].index(child_columns, self._backend)
        self._tables[parent_table].index(parent_columns, self._backend)
        self._relations[label] = _Relation(
            label, child_table, child_columns, parent_table, parent_columns, nulls, relationship
        )
        return self

    def validate(self) -> ValidationReport:
        """Validate snapshots without materializing joins or modifying their data."""
        tables: list[TableResult] = []
        relations: list[RelationResult] = []
        issues: list[Issue] = []

        def record(
            table_name: str,
            index: KeyIndex,
            positions: Sequence[int],
            code: str,
            relation: str | None = None,
        ) -> None:
            frame = self._tables[table_name].frame
            issues.extend(
                Issue(
                    "relation" if relation is not None else "table",
                    table_name,
                    relation,
                    code,
                    pos,
                    frame.index[pos],
                    index.keys[pos],
                )
                for pos in positions
            )

        for name, table in self._tables.items():
            if table.primary_key is None:
                tables.append(TableResult(name, len(table.frame), None, None, 0, 0, 0))
                continue
            index = table.index(table.primary_key, self._backend)
            record(name, index, index.null_positions, "primary_key_null")
            record(name, index, index.duplicate_positions, "primary_key_duplicate")
            tables.append(
                TableResult(
                    name,
                    len(table.frame),
                    table.primary_key,
                    not index.null_positions and not index.duplicate_keys,
                    len(index.null_positions),
                    len(index.duplicate_positions),
                    index.duplicate_keys,
                )
            )
        for relation in self._relations.values():
            child = self._tables[relation.child_table].index(relation.child_columns, self._backend)
            parent = self._tables[relation.parent_table].index(
                relation.parent_columns, self._backend
            )
            absent = {
                key: positions
                for key, positions in child.positions.items()
                if key not in parent.positions
            }
            orphan_positions = sorted(pos for positions in absent.values() for pos in positions)
            record(
                relation.child_table, child, orphan_positions, "foreign_key_orphan", relation.name
            )
            record(
                relation.parent_table,
                parent,
                parent.duplicate_positions,
                "foreign_key_target_duplicate",
                relation.name,
            )
            if relation.nulls == "forbid":
                record(
                    relation.child_table,
                    child,
                    child.null_positions,
                    "foreign_key_null",
                    relation.name,
                )
            if relation.relationship == "one_to_one":
                record(
                    relation.child_table,
                    child,
                    child.duplicate_positions,
                    "relation_child_duplicate",
                    relation.name,
                )
            valid = (
                not absent
                and not parent.duplicate_keys
                and (relation.nulls == "ignore" or not child.null_positions)
                and (relation.relationship == "many_to_one" or not child.duplicate_keys)
            )
            observed = f"{'many' if child.duplicate_keys else 'one'}_to_{'many' if parent.duplicate_keys else 'one'}"
            relations.append(
                RelationResult(
                    relation.name,
                    relation.child_table,
                    relation.parent_table,
                    relation.child_columns,
                    relation.parent_columns,
                    relation.nulls,
                    relation.relationship,
                    observed,
                    len(child.null_positions),
                    len(orphan_positions),
                    len(absent),
                    parent.duplicate_keys,
                    child.duplicate_keys,
                    valid,
                )
            )
        return ValidationReport(tuple(tables), tuple(relations), tuple(issues))
