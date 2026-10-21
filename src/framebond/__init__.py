"""Validate relational integrity across independent in-memory table snapshots."""

from .core import (
    Columns,
    DataModel,
    Issue,
    KeyBackend,
    KeyIndex,
    ModelError,
    NullPolicy,
    PandasBackend,
    Reference,
    RelationResult,
    Relationship,
    TableResult,
    ValidationReport,
)

__version__ = "0.1.0"
__all__ = [
    "Columns",
    "DataModel",
    "Issue",
    "KeyBackend",
    "KeyIndex",
    "ModelError",
    "NullPolicy",
    "PandasBackend",
    "Reference",
    "RelationResult",
    "Relationship",
    "TableResult",
    "ValidationReport",
]
